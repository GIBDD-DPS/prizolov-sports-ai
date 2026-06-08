# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.18 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Application configuration."""

from functools import cached_property
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "PRIZOLOV SPORTS AI"
    app_version: str = "14.14"
    amvera_app_name: str = "prizolov-sports"
    public_url: str = "https://prizolov-sports-dmandreyanov.amvera.io"
    api_prefix: str = "/api/v1"
    api_secret: str = ""

    database_url: str | None = None
    postgres_host: str = "amvera-dmandreyanov-cnpg-sports-rw"
    postgres_port: int = 5432
    postgres_user: str = ""
    postgres_password: str = ""
    postgres_db: str = "sports"
    postgres_sslmode: str = "disable"

    parser_enabled: bool = True
    parser_interval_minutes: int = 30
    parser_run_on_startup: bool = True
    parser_user_agent: str = (
        "PRIZOLOV-Sports-AI/14.14 (+https://prizolov-sports-dmandreyanov.amvera.io)"
    )

    @cached_property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url:
            return self._normalize_driver(self.database_url)

        if self.postgres_user and self.postgres_password:
            password = quote_plus(self.postgres_password)
            return (
                f"postgresql+psycopg2://{self.postgres_user}:{password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
                f"?sslmode={self.postgres_sslmode}"
            )

        return "sqlite:////data/prizolov.db"

    @staticmethod
    def _normalize_driver(url: str) -> str:
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url


settings = Settings()
