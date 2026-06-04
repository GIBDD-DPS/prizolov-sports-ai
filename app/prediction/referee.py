# Referee tendencies: cards, fouls, penalties.

from __future__ import annotations

from typing import Any, Dict, Optional


def referee_profile(
    *,
    referee_name: str = "",
    avg_yellows: float = 3.8,
    avg_fouls: float = 22.0,
    penalty_rate: float = 0.28,
    style: str = "balanced",
) -> Dict[str, Any]:
    return {
        "referee": referee_name or "unknown",
        "avg_yellow_cards": avg_yellows,
        "avg_fouls": avg_fouls,
        "penalty_rate_per_match": penalty_rate,
        "style": style,
        "cards_market_bias": "over" if avg_yellows >= 4.5 else "neutral",
        "fouls_market_bias": "over" if avg_fouls >= 25 else "neutral",
    }


def from_event(event: Dict[str, Any]) -> Dict[str, Any]:
    ref = event.get("referee") or {}
    if isinstance(ref, dict):
        return referee_profile(
            referee_name=str(ref.get("name") or ""),
            avg_yellows=float(ref.get("avg_yellows") or 3.8),
            avg_fouls=float(ref.get("avg_fouls") or 22),
            penalty_rate=float(ref.get("penalty_rate") or 0.28),
            style=str(ref.get("style") or "balanced"),
        )
    return referee_profile(referee_name=str(ref or ""))
