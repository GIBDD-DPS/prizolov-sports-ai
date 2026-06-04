# Starting lineups, injuries, suspensions, rotation risk.

from __future__ import annotations

from typing import Any, Dict, List, Optional


def assess_lineup_risk(
    event: Dict[str, Any],
    *,
    injuries_home: Optional[List[str]] = None,
    injuries_away: Optional[List[str]] = None,
    suspensions_home: Optional[List[str]] = None,
    suspensions_away: Optional[List[str]] = None,
    rotation_risk: str = "unknown",
    lineup_confirmed: bool = False,
) -> Dict[str, Any]:
    sport = str(event.get("sport") or "football")
    critical_sports = {"football", "basketball", "tennis"}
    ih = injuries_home or event.get("injuries_home") or []
    ia = injuries_away or event.get("injuries_away") or []
    sh = suspensions_home or event.get("suspensions_home") or []
    sa = suspensions_away or event.get("suspensions_away") or []
    rot = str(event.get("rotation_risk") or rotation_risk).lower()

    missing = len(ih) + len(ia) + len(sh) + len(sa)
    penalty = min(0.25, missing * 0.03)
    if rot in {"high", "heavy"}:
        penalty += 0.08
    if not lineup_confirmed and event.get("start_at") and sport in critical_sports:
        penalty += 0.06

    confidence = max(0.35, 1.0 - penalty)
    flags = []
    if ih or ia:
        flags.append("injuries")
    if sh or sa:
        flags.append("suspensions")
    if rot not in {"", "unknown", "low"}:
        flags.append(f"rotation_{rot}")

    return {
        "sport": sport,
        "lineup_confirmed": lineup_confirmed,
        "missing_players_total": missing,
        "confidence_multiplier": round(confidence, 3),
        "risk_flags": flags,
        "warning": "Проверьте стартовые составы за 1–2 ч до матча" if sport in critical_sports else None,
    }
