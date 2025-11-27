import os

from pydantic import BaseModel, Field


class DatabaseSettings(BaseModel):
    """
    Database connection settings loaded from environment variables.

    :return: configured database settings object
    """

    username: str = Field(default_factory=lambda: os.getenv("DB_USER", "root"))
    password: str = Field(default_factory=lambda: os.getenv("DB_PASSWORD", "password"))
    host: str = Field(default_factory=lambda: os.getenv("DB_HOST", "localhost"))
    port: int = Field(default_factory=lambda: int(os.getenv("DB_PORT", "3306")))
    name: str = Field(default_factory=lambda: os.getenv("DB_NAME", "allowances"))

    def url(self) -> str:
        """
        Build a full SQLAlchemy database URL.

        :return: a mysql+aiomysql URL assembled from the settings
        """

        return (
            "mysql+aiomysql://"
            f"{self.username}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}?charset=utf8mb4"
        )

    def sync_url(self) -> str:
        """
        Build a synchronous SQLAlchemy database URL for tooling.

        :return: a mysql+pymysql URL assembled from the settings
        """

        return (
            "mysql+pymysql://"
            f"{self.username}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}?charset=utf8mb4"
        )


class Settings(BaseModel):
    """
    Root application settings.

    :return: consolidated settings instance
    """

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)


settings = Settings()
