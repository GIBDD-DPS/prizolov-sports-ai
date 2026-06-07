# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.04 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Parser database settings (same CNPG cluster as backend)."""

import os
from urllib.parse import quote_plus


def get_database_url() -> str:
    if url := os.getenv("DATABASE_URL"):
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url

    host = os.getenv("POSTGRES_HOST", "amvera-dmandreyanov-cnpg-sports-rw")
    port = os.getenv("POSTGRES_PORT", "5432")
    user = os.getenv("POSTGRES_USER", "")
    password = os.getenv("POSTGRES_PASSWORD", "")
    db = os.getenv("POSTGRES_DB", "sports")
    sslmode = os.getenv("POSTGRES_SSLMODE", "disable")

    if user and password:
        return (
            f"postgresql+psycopg2://{user}:{quote_plus(password)}"
            f"@{host}:{port}/{db}?sslmode={sslmode}"
        )

    raise RuntimeError(
        "Database not configured. Set DATABASE_URL or POSTGRES_* env vars "
        "(host: amvera-dmandreyanov-cnpg-sports-rw)."
    )
