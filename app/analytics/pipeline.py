# Orchestrates v15 analytics on storefront events.

from __future__ import annotations

from typing import Any, Dict, List

from analytics.clv_tracker import clv_summary, record_bet_for_clv
from analytics.line_movement import (
    ingest_pinnacle_feed,
    line_monitor_status,
    line_movement_report,
    record_pari_lines_from_event,
)
from analytics.roi_monitor import roi_summary, settle_open_bets
from analytics.value_detector import scan_events_for_value
from analytics.xg_model import enrich_event_with_xg


def process_storefront_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    enriched: List[Dict[str, Any]] = []
    for raw in events:
        event = enrich_event_with_xg(dict(raw))
        record_pari_lines_from_event(event)
        enriched.append(event)

    value_signals = scan_events_for_value(enriched)
    settle_open_bets(value_signals)

    for sig in value_signals[:10]:
        ek = f"{sig.get('home')}|{sig.get('away')}|{sig.get('sport')}"
        record_bet_for_clv(
            event_key=ek,
            line=str(sig.get("line") or ""),
            bet_coefficient=float(sig.get("coefficient") or 1.5),
            closing_coefficient=float(sig.get("coefficient") or 1.5),
            bookmaker="pari",
        )

    ingest_pinnacle_feed(enriched)
    return enriched


def get_analytics_summary(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    value_signals = scan_events_for_value(events)
    return {
        "version": "15.0-analytics",
        "modules": {
            "xg_xga": {"enabled": True, "events_with_xg": sum(1 for e in events if e.get("xg_metrics"))},
            "clv": {"enabled": True, **clv_summary()},
            "value_detector": {
                "enabled": True,
                "signals_total": len(value_signals),
                "top_signals": value_signals[:15],
            },
            "roi_monitor": {"enabled": True, **roi_summary()},
            "line_movement": {
                "enabled": True,
                **line_monitor_status(),
                "active_moves": line_movement_report(limit=20),
            },
        },
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }
