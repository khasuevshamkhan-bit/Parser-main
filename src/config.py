import os

from pydantic import BaseModel, Field


class DatabaseSettings(BaseModel):
    """
    Database connection settings loaded from environment variables.
    """

    username: str = Field(default_factory=lambda: os.getenv("DB_USER", "postgres"))
    password: str = Field(default_factory=lambda: os.getenv("DB_PASSWORD", "postgres"))
    host: str = Field(default_factory=lambda: os.getenv("DB_HOST", "localhost"))
    port: int = Field(default_factory=lambda: int(os.getenv("DB_PORT", "5432")))
    name: str = Field(default_factory=lambda: os.getenv("DB_NAME", "allowances"))

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

    model_name: str = Field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base"))
    dimension: int = Field(default_factory=lambda: int(os.getenv("EMBEDDING_DIM", "768")))
    search_limit: int = Field(default_factory=lambda: int(os.getenv("VECTOR_SEARCH_LIMIT", "5")))
    load_timeout_seconds: float = Field(default_factory=lambda: float(os.getenv("EMBEDDING_LOAD_TIMEOUT", "120")))


class Settings(BaseModel):
    """
    Root application settings.
    """

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    vector: VectorSettings = Field(default_factory=VectorSettings)


settings = Settings()
