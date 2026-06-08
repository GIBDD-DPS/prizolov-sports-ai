# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.14 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Base parser adapter interface."""

from abc import ABC, abstractmethod
from typing import Any


class BaseSourceParser(ABC):
    source_id: str = "unknown"
    base_url: str = ""

    @abstractmethod
    async def fetch_football_events(self) -> list[dict[str, Any]]:
        """Fetch and parse football events from the source."""

    async def fetch(self) -> list[dict[str, Any]]:
        return await self.fetch_football_events()
