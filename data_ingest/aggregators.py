# ============================================
# Copyright (c) 2026
# Prizolov Agent OS v3.023
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


async def fetch_aggregators() -> List[Dict]:
    """Legacy scheduler hook; external odds aggregators removed."""
    logger.debug("Aggregators collector disabled (The Odds API removed)")
    return []
