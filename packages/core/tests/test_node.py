"""The node contract: declaration checks, run-time contract checks and result statuses."""

import pytest
from pydantic import ValidationError

from weta_core.errors import NodeContractError, NodeRegistrationError
from weta_core.hashing import compute_input_hash
from weta_core.node import (
    AssumptionUse,
    EngineModel,
    NodeRegistry,
    NodeResult,
    NodeStatus,
    NoParams,
    Tier,
    iter_quantities,
    node,
)
from weta_core.provenance import Layer, ProvenanceClass, TaintFlag, combine
from weta_core.quantity import Quantity

METHOD_REF = "docs/architecture.md#engine-contract"


class MassInput(EngineModel):
    concentration: Quantity | None
    volume: Quantity | None


class MassOutput(EngineModel):
    mass: Quantity


class OtherOutput(EngineModel):
    other: Quantity


def _mass(inp: MassInput, params: NoParams) -> NodeResult[MassOutput]:  # noqa: ARG001
    """Mass = concentration x volume (test fixture, not an engine)."""
    missing = tuple(name for name in ("concentration", "volume") if getattr(inp, name) is None)
    if missing:
        return NodeResult[MassOutput](status=NodeStatus.INSUFFICIENT_DATA, missing_inputs=missing)
    assert inp.concentration is not None
    assert inp.volume is not None
    product = inp.concentration * inp.volume
    cls, taint = combine(Layer.DERIVED, [inp.concentration, inp.volume])
    mass = product.to("kg").model_copy(update={"provenance": cls, "taint": taint})
    return NodeResult[MassOutput](status=NodeStatus.OK, output=MassOutput(mass=mass))


@pytest.fixture
def registry() -> NodeRegistry:
    return NodeRegistry()


def obs(value: float, unit: str, prov: ProvenanceClass = ProvenanceClass.OBSERVED) -> Quantity:
    return Quantity(value=value, unit=unit, provenance=prov)


class TestDeclaration:
    def test_registers_spec(self, registry: NodeRegistry) -> None:
        fn = node(
            id="test.mass",
            version="1.0.0",
            method_ref=METHOD_REF,
            layer=Layer.DERIVED,
            registry=registry,
        )(_mass)
        spec = registry.get("test.mass", "1.0.0")
        assert fn.spec is spec  # type: ignore[attr-defined]
        assert (spec.input_model, spec.params_model, spec.output_model) == (
            MassInput,
            NoParams,
            MassOutput,
        )
        assert len(registry) == 1
        assert list(registry) == [spec]

    @pytest.mark.parametrize(
        ("kwargs", "match"),
        [
            ({"id": "NoDots"}, "dotted lowercase"),
            ({"id": "single"}, "dotted lowercase"),
            ({"version": "1.0"}, "semantic"),
            ({"version": "01.0.0"}, "semantic"),
            ({"method_ref": "risk-engine.md"}, "doc anchor"),
        ],
    )
    def test_invalid_declarations(
        self, registry: NodeRegistry, kwargs: dict[str, str], match: str
    ) -> None:
        args = {"id": "test.mass", "version": "1.0.0", "method_ref": METHOD_REF} | kwargs
        with pytest.raises(NodeRegistrationError, match=match):
            node(**args, layer=Layer.DERIVED, registry=registry)  # type: ignore[arg-type]

    def test_duplicate_registration_rejected(self, registry: NodeRegistry) -> None:
        decl = node(
            id="test.mass",
            version="1.0.0",
            method_ref=METHOD_REF,
            layer=Layer.DERIVED,
            registry=registry,
        )
        decl(_mass)
        with pytest.raises(NodeRegistrationError, match="already registered"):
            decl(_mass)

    def test_unknown_node_lookup(self, registry: NodeRegistry) -> None:
        with pytest.raises(NodeRegistrationError, match="not registered"):
            registry.get("test.missing", "1.0.0")

    def test_signature_must_be_inputs_params_result(self, registry: NodeRegistry) -> None:
        decl = node(
            id="test.bad",
            version="1.0.0",
            method_ref=METHOD_REF,
            layer=Layer.DERIVED,
            registry=registry,
        )

        def one_arg(inp: MassInput) -> NodeResult[MassOutput]:
            raise NotImplementedError

        def plain_types(inp: int, params: NoParams) -> NodeResult[MassOutput]:
            raise NotImplementedError

        def bare_return(inp: MassInput, params: NoParams) -> MassOutput:
            raise NotImplementedError

        for bad in (one_arg, plain_types, bare_return):
            with pytest.raises(NodeRegistrationError):
                decl(bad)


class TestExecution:
    def test_hand_calculated_reference(self, registry: NodeRegistry) -> None:
        fn = node(
            id="test.mass",
            version="1.0.0",
            method_ref=METHOD_REF,
            layer=Layer.DERIVED,
            registry=registry,
        )(_mass)
        # 2 g/L = 2 kg/m3; 2 kg/m3 x 3 m3 = 6 kg
        result = fn(MassInput(concentration=obs(2.0, "g/L"), volume=obs(3.0, "m**3")), NoParams())
        assert result.status is NodeStatus.OK
        assert result.output.mass.value == pytest.approx(6.0)
        assert result.output.mass.unit == "kg"
        assert result.output.mass.provenance is ProvenanceClass.DERIVED

    def test_taint_flows_into_output(self, registry: NodeRegistry) -> None:
        fn = node(
            id="test.mass",
            version="1.0.0",
            method_ref=METHOD_REF,
            layer=Layer.DERIVED,
            registry=registry,
        )(_mass)
        inp = MassInput(
            concentration=obs(2.0, "g/L", ProvenanceClass.PREDICTED),
            volume=obs(3.0, "m**3", ProvenanceClass.SYNTHETIC_DEMO),
        )
        mass = fn(inp, NoParams()).output.mass
        assert mass.taint == frozenset({TaintFlag.PREDICTED, TaintFlag.SYNTHETIC})

    def test_missing_input_gives_insufficient_data_not_a_guess(
        self, registry: NodeRegistry
    ) -> None:
        fn = node(
            id="test.mass",
            version="1.0.0",
            method_ref=METHOD_REF,
            layer=Layer.DERIVED,
            registry=registry,
        )(_mass)
        result = fn(MassInput(concentration=None, volume=obs(3.0, "m**3")), NoParams())
        assert result.status is NodeStatus.INSUFFICIENT_DATA
        assert result.missing_inputs == ("concentration",)
        assert result.output is None

    def test_wrong_input_or_params_type(self, registry: NodeRegistry) -> None:
        fn = node(
            id="test.mass",
            version="1.0.0",
            method_ref=METHOD_REF,
            layer=Layer.DERIVED,
            registry=registry,
        )(_mass)
        with pytest.raises(NodeContractError, match="inputs"):
            fn(NoParams(), NoParams())
        with pytest.raises(NodeContractError, match="params"):
            fn(
                MassInput(concentration=None, volume=None),
                MassInput(concentration=None, volume=None),
            )

    def test_output_provenance_must_match_layer(self, registry: NodeRegistry) -> None:
        @node(
            id="test.ml",
            version="1.0.0",
            method_ref=METHOD_REF,
            layer=Layer.PREDICTED,
            registry=registry,
        )
        def leaky(inp: MassInput, params: NoParams) -> NodeResult[MassOutput]:  # noqa: ARG001
            # An ML node trying to emit a value that is not PREDICTED.
            return NodeResult[MassOutput](
                status=NodeStatus.OK,
                output=MassOutput(mass=obs(1.0, "kg", ProvenanceClass.DERIVED)),
            )

        with pytest.raises(NodeContractError, match="must emit PREDICTED"):
            leaky(MassInput(concentration=None, volume=None), NoParams())

    def test_return_type_is_checked(self, registry: NodeRegistry) -> None:
        @node(
            id="test.wrong",
            version="1.0.0",
            method_ref=METHOD_REF,
            layer=Layer.DERIVED,
            registry=registry,
        )
        def wrong_output(inp: MassInput, params: NoParams) -> NodeResult[MassOutput]:  # noqa: ARG001
            other = OtherOutput(other=obs(1.0, "kg", ProvenanceClass.DERIVED))
            return NodeResult[OtherOutput](status=NodeStatus.OK, output=other)  # type: ignore[return-value]

        @node(
            id="test.none",
            version="1.0.0",
            method_ref=METHOD_REF,
            layer=Layer.DERIVED,
            registry=registry,
        )
        def not_a_result(inp: MassInput, params: NoParams) -> NodeResult[MassOutput]:  # noqa: ARG001
            return None  # type: ignore[return-value]

        empty = MassInput(concentration=None, volume=None)
        with pytest.raises(NodeContractError, match="output must be MassOutput"):
            wrong_output(empty, NoParams())
        with pytest.raises(NodeContractError, match="NodeResult"):
            not_a_result(empty, NoParams())

    def test_spec_input_hash(self, registry: NodeRegistry) -> None:
        node(
            id="test.mass",
            version="1.0.0",
            method_ref=METHOD_REF,
            layer=Layer.DERIVED,
            registry=registry,
        )(_mass)
        spec = registry.get("test.mass", "1.0.0")
        inp = MassInput(concentration=obs(2.0, "g/L"), volume=obs(3.0, "m**3"))
        expected = compute_input_hash(
            node_id="test.mass", node_version="1.0.0", inputs=inp, method_params=NoParams(), seed=7
        )
        assert spec.input_hash(inp, NoParams(), seed=7) == expected
        assert spec.input_hash(inp, NoParams(), seed=8) != expected


class TestNodeResult:
    def test_ok_needs_output(self) -> None:
        with pytest.raises(ValidationError, match="requires an output"):
            NodeResult[MassOutput](status=NodeStatus.OK)

    def test_ok_cannot_list_missing(self) -> None:
        out = MassOutput(mass=obs(1.0, "kg", ProvenanceClass.DERIVED))
        with pytest.raises(ValidationError, match="missing inputs"):
            NodeResult[MassOutput](status=NodeStatus.OK, output=out, missing_inputs=("x",))

    def test_insufficient_data_needs_missing_list_and_no_output(self) -> None:
        with pytest.raises(ValidationError, match="list of missing inputs"):
            NodeResult[MassOutput](status=NodeStatus.INSUFFICIENT_DATA)
        out = MassOutput(mass=obs(1.0, "kg", ProvenanceClass.DERIVED))
        with pytest.raises(ValidationError, match="never emit a guess"):
            NodeResult[MassOutput](
                status=NodeStatus.INSUFFICIENT_DATA, output=out, missing_inputs=("x",)
            )

    @pytest.mark.parametrize(
        "status", [NodeStatus.OUT_OF_VALIDITY_RANGE, NodeStatus.NOT_APPLICABLE]
    )
    def test_other_statuses_need_a_reason(self, status: NodeStatus) -> None:
        with pytest.raises(ValidationError, match="requires a reason"):
            NodeResult[MassOutput](status=status)
        result = NodeResult[MassOutput](
            status=status, reason="outside 0-100 degC", tier=Tier.SCREENING
        )
        assert result.tier is Tier.SCREENING

    def test_assumption_codes_follow_the_register_format(self) -> None:
        assert AssumptionUse(code="A-MB-04").code == "A-MB-04"
        with pytest.raises(ValidationError):
            AssumptionUse(code="mass-balance tolerance")


def test_iter_quantities_paths() -> None:
    nested = {
        "a": obs(1.0, "kg"),
        "items": [MassOutput(mass=obs(2.0, "kg")), "not a quantity"],
    }
    assert [path for path, _ in iter_quantities(nested)] == ["a", "items.0.mass"]
