"""The engine node contract: ``@node``, ``NodeResult`` and the node registry.

docs/architecture.md section 4 ("Engine contract") and docs/development-rules.md section B.
Every engine exposes pure node functions of the form::

    @node(id="groundwater.screening", version="1.0.0",
          method_ref="docs/risk-engine.md#groundwater", layer=Layer.MODELLED)
    def groundwater_screening(inp: GroundwaterInput, params: GroundwaterParams
                              ) -> NodeResult[GroundwaterOutput]: ...

The decorator records the declaration, checks the call against it at run time, and checks
that every output quantity carries the provenance class of the node's layer, so for example
an ML node can never emit a value that is not ``PREDICTED``.
"""

import re
import typing
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from weta_core.errors import NodeContractError, NodeRegistrationError
from weta_core.hashing import compute_input_hash
from weta_core.provenance import Layer
from weta_core.quantity import Quantity

NODE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
SEMVER_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
METHOD_REF_PATTERN = re.compile(r"^docs/[a-z0-9_\-/]+\.md#[a-z0-9\-]+$")
ASSUMPTION_CODE_PATTERN = r"^A-[A-Z]+-\d{2}$"


class EngineModel(BaseModel):
    """Base class for engine input, output and parameter models: frozen, no unknown fields."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class NoParams(EngineModel):
    """Parameter model for nodes that take no method parameters."""


class NodeStatus(StrEnum):
    """Outcome of one node execution (docs/architecture.md section 4)."""

    OK = "ok"
    INSUFFICIENT_DATA = "insufficient_data"
    OUT_OF_VALIDITY_RANGE = "out_of_validity_range"
    NOT_APPLICABLE = "not_applicable"


class Tier(StrEnum):
    """Model tier (docs/environmental-models.md, general rules)."""

    SCREENING = "screening"
    REFINED = "refined"


class AssumptionUse(EngineModel):
    """A registered assumption used by a run, with the value used if it has one."""

    code: str = Field(pattern=ASSUMPTION_CODE_PATTERN)
    value: Quantity | None = None


class NodeResult[OutT: BaseModel](EngineModel):
    """Result of a node: a status, the output if any, and everything needed to explain it."""

    status: NodeStatus
    output: OutT | None = None
    missing_inputs: tuple[str, ...] = ()
    reason: str | None = None
    warnings: tuple[str, ...] = ()
    assumptions_used: tuple[AssumptionUse, ...] = ()
    limitations: tuple[str, ...] = ()
    tier: Tier | None = None

    @model_validator(mode="after")
    def _status_consistency(self) -> Self:
        if self.status is NodeStatus.OK:
            if self.output is None:
                msg = "status ok requires an output"
                raise ValueError(msg)
            if self.missing_inputs:
                msg = "status ok cannot list missing inputs"
                raise ValueError(msg)
        else:
            if self.output is not None:
                msg = f"status {self.status} must not carry an output; never emit a guess"
                raise ValueError(msg)
            if self.status is NodeStatus.INSUFFICIENT_DATA and not self.missing_inputs:
                msg = "insufficient_data requires the list of missing inputs"
                raise ValueError(msg)
            if self.status is not NodeStatus.INSUFFICIENT_DATA and not self.reason:
                msg = f"status {self.status} requires a reason"
                raise ValueError(msg)
        return self


@dataclass(frozen=True)
class NodeSpec:
    """A registered node declaration (docs/development-rules.md B.3)."""

    id: str
    version: str
    method_ref: str
    layer: Layer
    input_model: type[BaseModel]
    params_model: type[BaseModel]
    output_model: type[BaseModel]
    validity: Mapping[str, str]
    func: Callable[..., NodeResult[Any]] = field(repr=False)

    @property
    def key(self) -> tuple[str, str]:
        """Registry key: node id and version."""
        return (self.id, self.version)

    def input_hash(
        self,
        inputs: BaseModel,
        params: BaseModel,
        *,
        dataset_version_ids: typing.Iterable[UUID] = (),
        model_version_id: UUID | None = None,
        seed: int | None = None,
    ) -> str:
        """Run identity for executing this node on ``inputs`` with ``params``."""
        return compute_input_hash(
            node_id=self.id,
            node_version=self.version,
            inputs=inputs,
            method_params=params,
            dataset_version_ids=dataset_version_ids,
            model_version_id=model_version_id,
            seed=seed,
        )


class NodeRegistry:
    """Registry of node declarations, keyed by ``(id, version)``."""

    def __init__(self) -> None:
        self._nodes: dict[tuple[str, str], NodeSpec] = {}

    def register(self, spec: NodeSpec) -> None:
        """Add a node. Registering the same id and version twice is an error."""
        if spec.key in self._nodes:
            msg = f"node {spec.id}@{spec.version} is already registered"
            raise NodeRegistrationError(msg)
        self._nodes[spec.key] = spec

    def get(self, node_id: str, version: str) -> NodeSpec:
        """Look up a node by id and version."""
        try:
            return self._nodes[(node_id, version)]
        except KeyError:
            msg = f"node {node_id}@{version} is not registered"
            raise NodeRegistrationError(msg) from None

    def __iter__(self) -> Iterator[NodeSpec]:
        return iter(sorted(self._nodes.values(), key=lambda s: s.key))

    def __len__(self) -> int:
        return len(self._nodes)


default_registry = NodeRegistry()


def iter_quantities(obj: object) -> Iterator[tuple[str, Quantity]]:
    """Yield ``(path, quantity)`` for every ``Quantity`` nested in a model, mapping or sequence."""
    if isinstance(obj, Quantity):
        yield ("", obj)
    elif isinstance(obj, BaseModel):
        for name, value in obj:
            for path, q in iter_quantities(value):
                yield (f"{name}.{path}" if path else name, q)
    elif isinstance(obj, Mapping):
        for key, value in obj.items():
            for path, q in iter_quantities(value):
                yield (f"{key}.{path}" if path else str(key), q)
    elif isinstance(obj, list | tuple | set | frozenset):
        for i, value in enumerate(obj):
            for path, q in iter_quantities(value):
                yield (f"{i}.{path}" if path else str(i), q)


def _resolve_signature(
    func: Callable[..., Any],
) -> tuple[type[BaseModel], type[BaseModel], type[BaseModel]]:
    hints = typing.get_type_hints(func)
    params = [p for p in hints if p != "return"]
    if len(params) != 2:
        msg = f"{func.__qualname__}: a node takes exactly (inputs, params)"
        raise NodeRegistrationError(msg)
    input_model, params_model = hints[params[0]], hints[params[1]]
    ret = hints.get("return")
    for label, model in (("inputs", input_model), ("params", params_model)):
        if not (isinstance(model, type) and issubclass(model, BaseModel)):
            msg = f"{func.__qualname__}: {label} must be annotated with a pydantic model"
            raise NodeRegistrationError(msg)
    meta = getattr(ret, "__pydantic_generic_metadata__", None)
    if not meta or meta.get("origin") is not NodeResult or not meta.get("args"):
        msg = f"{func.__qualname__}: return type must be NodeResult[OutputModel]"
        raise NodeRegistrationError(msg)
    output_model = meta["args"][0]
    return input_model, params_model, output_model


def node(
    *,
    id: str,  # noqa: A002 - "id" is the documented name of the declaration field
    version: str,
    method_ref: str,
    layer: Layer,
    validity: Mapping[str, str] | None = None,
    registry: NodeRegistry | None = None,
) -> Callable[[Callable[..., NodeResult[Any]]], Callable[..., NodeResult[Any]]]:
    """Declare and register an engine node.

    ``validity`` describes the validity range in words per input (for example
    ``{"temperature": "273.15 K to 373.15 K"}``); the node itself must return
    ``out_of_validity_range`` outside it (docs/development-rules.md B.4).
    """
    if not NODE_ID_PATTERN.match(id):
        msg = f"node id {id!r} must be dotted lowercase, for example 'waste.generation'"
        raise NodeRegistrationError(msg)
    if not SEMVER_PATTERN.match(version):
        msg = f"node version {version!r} must be semantic MAJOR.MINOR.PATCH"
        raise NodeRegistrationError(msg)
    if not METHOD_REF_PATTERN.match(method_ref):
        msg = f"method_ref {method_ref!r} must point at a doc anchor, e.g. 'docs/x.md#anchor'"
        raise NodeRegistrationError(msg)
    target = default_registry if registry is None else registry

    def decorator(func: Callable[..., NodeResult[Any]]) -> Callable[..., NodeResult[Any]]:
        input_model, params_model, output_model = _resolve_signature(func)

        def wrapper(inputs: BaseModel, params: BaseModel) -> NodeResult[Any]:
            if not isinstance(inputs, input_model):
                msg = f"{id}: inputs must be {input_model.__name__}"
                raise NodeContractError(msg)
            if not isinstance(params, params_model):
                msg = f"{id}: params must be {params_model.__name__}"
                raise NodeContractError(msg)
            result: object = func(inputs, params)
            if not isinstance(result, NodeResult):
                msg = f"{id}: must return a NodeResult"
                raise NodeContractError(msg)
            if result.output is not None:
                if not isinstance(result.output, output_model):
                    msg = f"{id}: output must be {output_model.__name__}"
                    raise NodeContractError(msg)
                for path, q in iter_quantities(result.output):
                    if q.provenance is not layer.provenance:
                        msg = (
                            f"{id}: output {path} has provenance {q.provenance}, "
                            f"but a {layer} node must emit {layer.provenance}"
                        )
                        raise NodeContractError(msg)
            return result

        wrapper.__name__ = func.__name__
        wrapper.__qualname__ = func.__qualname__
        wrapper.__doc__ = func.__doc__
        spec = NodeSpec(
            id=id,
            version=version,
            method_ref=method_ref,
            layer=layer,
            input_model=input_model,
            params_model=params_model,
            output_model=output_model,
            validity=dict(validity or {}),
            func=wrapper,
        )
        target.register(spec)
        wrapper.spec = spec  # type: ignore[attr-defined]
        return wrapper

    return decorator
