# ============================================
# Copyright (c) 2026
# Prizolov Agent OS v3.023
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


async def fetch_free_apis() -> Dict[str, List]:
    """Legacy scheduler hook; API-Football integration removed."""
    logger.debug("Free APIs collector disabled (API-Football removed)")
    return {"live": [], "upcoming": []}
