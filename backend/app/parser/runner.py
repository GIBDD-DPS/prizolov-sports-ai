# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.18 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Parser runner — invoked by scheduler and admin endpoint."""

import asyncio
import logging

from app.parser.persistence import persist_source_error, persist_source_events
from app.parser.sources import PARSERS

logger = logging.getLogger("prizolov.parser")


async def run_all() -> dict:
    logger.info("PRIZOLOV SPORTS AI — parser run started")
    results: dict[str, int | str] = {}

    for parser in PARSERS:
        try:
            events = await parser.fetch()
            fetched_count = len(events)
            persisted_count = persist_source_events(parser.source_id, events)
            results[parser.source_id] = persisted_count
            logger.info(
                "%s: fetched %d items, persisted %d",
                parser.source_id,
                fetched_count,
                persisted_count,
            )
        except Exception as exc:
            results[parser.source_id] = f"error: {exc}"
            persist_source_error(parser.source_id, str(exc))
            logger.exception("Parser failed: %s", parser.source_id)

    logger.info("Parser run finished")
    return results


if __name__ == "__main__":
    asyncio.run(run_all())
