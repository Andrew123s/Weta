"""RFC 9457 problem details, the single error format of the API (docs/api.md, conventions)."""

from pydantic import BaseModel, ConfigDict, Field

PROBLEM_CONTENT_TYPE = "application/problem+json"


class FieldError(BaseModel):
    """One validation error, located by a JSON-pointer-like path."""

    model_config = ConfigDict(extra="forbid")

    loc: list[str | int] = Field(description="Path to the offending field")
    msg: str
    type: str


class ProblemDetail(BaseModel):
    """Error response body. Never contains stack traces or internal details."""

    model_config = ConfigDict(extra="forbid")

    type: str = Field(default="about:blank", description="URI identifying the problem type")
    title: str
    status: int = Field(ge=400, le=599)
    detail: str | None = None
    instance: str | None = None
    errors: list[FieldError] = Field(default_factory=list)
    request_id: str | None = None
