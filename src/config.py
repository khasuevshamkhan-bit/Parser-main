import os

from pydantic import BaseModel, Field


def _require_env(name: str) -> str:
    """
    Fetch a required environment variable or raise a clear error.
    """

    value = os.getenv(key=name)
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
    min_score_threshold: float = Field(default=0.0)
    search_metric: str = Field(default="cosine")
    rerank_model_name: str = Field(default="cross-encoder/ms-marco-MiniLM-L-6-v2")
    rerank_candidates: int = Field(default=20)
    rerank_top_k: int = Field(default=5)
    enable_rerank: bool = Field(default=True)


class Settings(BaseModel):
    """
    Root application settings.
    """

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    vector: VectorSettings = Field(default_factory=VectorSettings)


settings = Settings()
