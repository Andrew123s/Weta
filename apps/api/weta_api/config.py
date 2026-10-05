"""Application settings, read from environment variables (prefix ``WETA_``) or ``.env``.

docs/deployment.md section 4. Secrets are ``SecretStr`` so they never appear in logs or reprs.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Unknown ``WETA_`` variables are ignored."""

    model_config = SettingsConfigDict(env_prefix="WETA_", env_file=".env", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    database_url: SecretStr | None = None
    migration_database_url: SecretStr | None = None
    db_check_timeout_s: float = Field(default=3.0, gt=0, le=30)

    secret_key: SecretStr | None = None

    allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    file_store_root: Path = Path("./var/filestore")
    max_upload_mb: int = Field(default=200, gt=0)

    git_sha: str | None = Field(default=None, pattern=r"^[0-9a-f]{7,40}$")

    @field_validator("database_url", "migration_database_url", "secret_key", mode="before")
    @classmethod
    def _empty_is_none(cls, v: object) -> object:
        return None if isinstance(v, str) and not v.strip() else v

    @model_validator(mode="after")
    def _production_rules(self) -> "Settings":
        if self.environment == "production" and "*" in self.allowed_origins:
            msg = "wildcard CORS origins are not allowed in production"
            raise ValueError(msg)
        return self


@lru_cache
def get_settings() -> Settings:
    """Process-wide settings instance."""
    return Settings()
