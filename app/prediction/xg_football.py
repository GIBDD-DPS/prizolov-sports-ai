# Football xG module: xG, xGA, big chances, SOT, PPDA, possession.

from __future__ import annotations

from typing import Any, Dict, Optional

from analytics.xg_model import estimate_xg_xga


def _num(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def build_football_xg_profile(event: Dict[str, Any], external: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Merge scraped/live event with optional external stats feed.
    external keys: big_chances_h, big_chances_a, sot_h, sot_a, ppda_h, ppda_a, possession_h
    """
    ext = external or {}
    base = estimate_xg_xga(event)
    if str(event.get("sport") or "").lower() != "football":
        return {**base, "football_extended": False}

    xg_h = _num(base.get("xg_home"), 1.35)
    xg_a = _num(base.get("xg_away"), 1.15)
    sot_h = _num(ext.get("shots_on_target_h"), xg_h * 2.8)
    sot_a = _num(ext.get("shots_on_target_a"), xg_a * 2.8)
    bc_h = _num(ext.get("big_chances_h"), xg_h * 0.9)
    bc_a = _num(ext.get("big_chances_a"), xg_a * 0.9)
    ppda_h = _num(ext.get("ppda_h"), 10.0)
    ppda_a = _num(ext.get("ppda_a"), 10.0)
    poss_h = _num(ext.get("possession_h"), 50.0)

    # Attack pressure index tweaks xG
    pressure_h = (sot_h * 0.04 + bc_h * 0.12 + poss_h * 0.006) - (ppda_h * 0.008)
    pressure_a = (sot_a * 0.04 + bc_a * 0.12 + (100 - poss_h) * 0.006) - (ppda_a * 0.008)
    adj_xg_h = max(0.2, xg_h + pressure_h)
    adj_xg_a = max(0.2, xg_a + pressure_a)

    return {
        **base,
        "football_extended": True,
        "xg": round(adj_xg_h, 3),
        "xga": round(adj_xg_a, 3),
        "xg_home": round(adj_xg_h, 3),
        "xg_away": round(adj_xg_a, 3),
        "xga_home": round(adj_xg_a, 3),
        "xga_away": round(adj_xg_h, 3),
        "big_chances_home": round(bc_h, 2),
        "big_chances_away": round(bc_a, 2),
        "shots_on_target_home": round(sot_h, 2),
        "shots_on_target_away": round(sot_a, 2),
        "ppda_home": round(ppda_h, 2),
        "ppda_away": round(ppda_a, 2),
        "possession_home": round(poss_h, 1),
    }


def xg_to_1x2(profile: Dict[str, Any]) -> Dict[str, float]:
    """Poisson-style 1X2 from adjusted xG (lightweight, no scipy dep)."""
    import math

    lh = max(0.15, _num(profile.get("xg_home"), 1.3))
    la = max(0.15, _num(profile.get("xg_away"), 1.1))

    def pois_pmf(k: int, lam: float) -> float:
        return math.exp(-lam) * (lam**k) / math.factorial(k)

    p_h = p_d = p_a = 0.0
    for i in range(8):
        for j in range(8):
            p = pois_pmf(i, lh) * pois_pmf(j, la)
            if i > j:
                p_h += p
            elif i == j:
                p_d += p
            else:
                p_a += p
    total = p_h + p_d + p_a or 1.0
    return {
        "home_win": round(p_h / total, 4),
        "draw": round(p_d / total, 4),
        "away_win": round(p_a / total, 4),
    }
