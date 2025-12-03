import os

from pydantic import BaseModel, Field


def _require_env(name: str) -> str:
    """Fetch a required environment variable or raise a clear error."""

    value = os.getenv(name)
    if value is None or value == "":
        raise EnvironmentError(
            f"Environment variable {name} is required but not set."
        )
    return value


class DatabaseSettings(BaseModel):
    """
    Database connection settings loaded from environment variables.
    """

    username: str = Field(default_factory=lambda: _require_env("DB_USER"))
    password: str = Field(default_factory=lambda: _require_env("DB_PASSWORD"))
    host: str = Field(default_factory=lambda: _require_env("DB_HOST"))
    port: int = Field(default_factory=lambda: int(_require_env("DB_PORT")))
    name: str = Field(default_factory=lambda: _require_env("DB_NAME"))

    def url(self) -> str:
        """
        Build an asynchronous PostgreSQL URL for application use.
        """

        return (
            "postgresql+asyncpg://"
            f"{self.username}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )

    def sync_url(self) -> str:
        """
        Build a synchronous PostgreSQL URL for migration tooling.
        """

        return (
            "postgresql+psycopg://"
            f"{self.username}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}"
        )


class VectorSettings(BaseModel):
    """
    Parameters for embedding generation and vector storage.
    """

    backend: str = Field(default_factory=lambda: _require_env("EMBEDDING_BACKEND"))
    model_name: str = Field(default_factory=lambda: _require_env("EMBEDDING_MODEL"))
    dimension: int = Field(default_factory=lambda: int(_require_env("EMBEDDING_DIM")))
    search_limit: int = Field(
        default_factory=lambda: int(_require_env("VECTOR_SEARCH_LIMIT"))
    )
    load_timeout_seconds: float = Field(
        default_factory=lambda: float(_require_env("EMBEDDING_LOAD_TIMEOUT"))
    )
    offline: bool = Field(
        default_factory=lambda: _require_env("EMBEDDING_OFFLINE").lower()
        in {"1", "true", "yes", "on"}
    )
    local_model_path: str | None = Field(
        default_factory=lambda: _require_env("EMBEDDING_LOCAL_MODEL")
    )


class Settings(BaseModel):
    """
    Root application settings.
    """

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    vector: VectorSettings = Field(default_factory=VectorSettings)


settings = Settings()
