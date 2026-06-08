# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.14 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Parser runner — invoked by scheduler and admin endpoint."""

import asyncio
import logging

from app.parser.sources import PARSERS

logger = logging.getLogger("prizolov.parser")


async def run_all() -> dict:
    logger.info("PRIZOLOV SPORTS AI — parser run started")
    results: dict[str, int | str] = {}

    for parser in PARSERS:
        try:
            events = await parser.fetch()
            count = len(events)
            results[parser.source_id] = count
            logger.info("%s: fetched %d items", parser.source_id, count)
        except Exception as exc:
            results[parser.source_id] = f"error: {exc}"
            logger.exception("Parser failed: %s", parser.source_id)

    logger.info("Parser run finished")
    return results


if __name__ == "__main__":
    asyncio.run(run_all())
