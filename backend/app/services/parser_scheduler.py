# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.18 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Background parser scheduler for single-app Amvera deployment."""

import asyncio
import logging

from app.core.config import settings
from app.parser.runner import run_all

logger = logging.getLogger("prizolov.scheduler")


async def parser_loop() -> None:
    interval = settings.parser_interval_minutes * 60
    logger.info(
        "Parser scheduler started (every %s min, run_on_startup=%s)",
        settings.parser_interval_minutes,
        settings.parser_run_on_startup,
    )

    if settings.parser_run_on_startup:
        await run_all()

    while True:
        await asyncio.sleep(interval)
        await run_all()


def start_parser_scheduler() -> asyncio.Task | None:
    if not settings.parser_enabled:
        logger.info("Parser scheduler disabled (PARSER_ENABLED=false)")
        return None
    return asyncio.create_task(parser_loop(), name="parser-scheduler")
