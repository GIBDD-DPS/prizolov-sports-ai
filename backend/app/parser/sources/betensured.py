# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.06 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""ru.betensured.com football predictions parser — Step 5 implementation."""

from typing import Any

import httpx

from app.core.config import settings
from app.parser.sources.base import BaseSourceParser


class BetensuredParser(BaseSourceParser):
    source_id = "betensured"
    base_url = "https://ru.betensured.com"

    async def fetch_football_events(self) -> list[dict[str, Any]]:
        headers = {"User-Agent": settings.parser_user_agent}
        async with httpx.AsyncClient(timeout=30.0, headers=headers, follow_redirects=True) as client:
            response = await client.get(self.base_url)
            response.raise_for_status()
            return [{"source_id": self.source_id, "raw_length": len(response.text)}]
