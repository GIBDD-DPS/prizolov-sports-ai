# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.18 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Parser runner — invoked by scheduler and admin endpoint."""

import asyncio
import logging

from app.db.session import SessionLocal
from app.engine.accuracy import reconcile_finished_events
from app.engine.predictor import rebuild_predictions
from app.parser.persistence import persist_source_error, persist_source_events
from app.parser.sources import PARSERS
from app.agenomics_integration import PARSER_AGENT, FORECAST_AGENT

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
            PARSER_AGENT.record_success()
            logger.info(
                "%s: fetched %d items, persisted %d",
                parser.source_id,
                fetched_count,
                persisted_count,
            )
        except Exception as exc:
            results[parser.source_id] = f"error: {exc}"
            persist_source_error(parser.source_id, str(exc))
            PARSER_AGENT.record_failure(exc)
            logger.exception("Parser failed: %s", parser.source_id)

    db = SessionLocal()
    try:
        predictions_written = rebuild_predictions(db)
        results["predictions"] = predictions_written
        FORECAST_AGENT.record_success()
        logger.info("Predictions rebuilt: %d", predictions_written)
    except Exception as exc:
        results["predictions"] = f"error: {exc}"
        FORECAST_AGENT.record_failure(exc)
        logger.exception("Predictions rebuild failed")
    finally:
        db.close()

    # Сверка прогнозов с фактическими исходами уже завершившихся матчей.
    db = SessionLocal()
    try:
        reconciled = await reconcile_finished_events(db)
        results["reconciled"] = reconciled
        if reconciled:
            logger.info("Reconciled %d finished events with actual outcomes", reconciled)
    except Exception as exc:
        results["reconciled"] = f"error: {exc}"
        logger.exception("Accuracy reconciliation failed")
    finally:
        db.close()

    try:
        parser_trust = PARSER_AGENT.score()
        forecast_trust = FORECAST_AGENT.score()
        results["trust"] = {
            PARSER_AGENT.agent_id: parser_trust.score,
            FORECAST_AGENT.agent_id: forecast_trust.score,
        }
    except RuntimeError as exc:
        logger.warning("Agenomics недоступен: %s", exc)

    logger.info("Parser run finished")
    return results


if __name__ == "__main__":
    asyncio.run(run_all())
