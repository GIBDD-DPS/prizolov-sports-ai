# Pure metric formulas: accuracy, ROI, yield, Brier, EV, Kelly.

from __future__ import annotations

from typing import Any, Dict, Optional


def implied_probability(coefficient: float) -> float:
    if coefficient < 1.01:
        return 0.0
    return min(1.0, 1.0 / coefficient)


def win_rate(wins: int, total: int, *, push: int = 0, void: int = 0) -> float:
    settled = total - push - void
    if settled <= 0:
        return 0.0
    return round(wins / settled, 4)


def roi_percent(profit: float, stake: float) -> float:
    if stake <= 0:
        return 0.0
    return round((profit / stake) * 100.0, 2)


def yield_per_bet(profit: float, num_bets: int) -> float:
    if num_bets <= 0:
        return 0.0
    return round(profit / num_bets, 3)


def brier_score(probability: float, outcome: int) -> float:
    """outcome: 1 win, 0 loss."""
    p = max(0.0, min(1.0, float(probability)))
    o = 1 if int(outcome) else 0
    return round((p - o) ** 2, 4)


def expected_value_percent(probability: float, odds: float) -> float:
    """EV% = (p * odds - 1) * 100."""
    p = max(0.0, min(1.0, float(probability)))
    o = max(1.01, float(odds))
    return round((p * o - 1.0) * 100.0, 2)


def value_percent(model_probability: float, bookmaker_coefficient: float) -> float:
    book_p = implied_probability(bookmaker_coefficient)
    return round((float(model_probability) - book_p) * 100.0, 2)


def kelly_stake_percent(probability: float, odds: float, *, fraction: float = 0.25) -> float:
    """Fractional Kelly as % of bankroll (capped 0–5%)."""
    p = max(0.001, min(0.99, float(probability)))
    b = max(0.01, float(odds) - 1.0)
    q = 1.0 - p
    kelly = (b * p - q) / b
    kelly = max(0.0, kelly) * float(fraction)
    return round(min(5.0, kelly * 100.0), 2)


def risk_level(
    *,
    confidence: int,
    value_pct: float,
    lineup_unconfirmed: bool = False,
    line_moves: int = 0,
) -> str:
    if lineup_unconfirmed and line_moves >= 2:
        return "HIGH"
    if confidence >= 80 and value_pct >= 5.0 and line_moves < 2:
        return "LOW"
    if confidence >= 65 or value_pct >= 3.0:
        return "MEDIUM"
    return "HIGH"


def score_bet_display(
    model_probability: float,
    coefficient: float,
    *,
    confidence_base: Optional[int] = None,
    lineup_unconfirmed: bool = False,
    line_moves: int = 0,
) -> Dict[str, Any]:
    book_p = implied_probability(coefficient)
    model_p = max(0.0, min(1.0, float(model_probability)))
    val = value_percent(model_p, coefficient)
    ev = expected_value_percent(model_p, coefficient)
    margin = abs(model_p - book_p)
    confidence = confidence_base if confidence_base is not None else min(100, int(50 + margin * 100 + (5 if val > 0 else 0)))
    risk = risk_level(confidence=confidence, value_pct=val, lineup_unconfirmed=lineup_unconfirmed, line_moves=line_moves)
    kelly = kelly_stake_percent(model_p, coefficient)
    return {
        "confidence": confidence,
        "confidence_label": f"{confidence}/100",
        "value_percent": val,
        "value_label": f"{val:+.1f}%",
        "bookmaker_probability_percent": round(book_p * 100, 1),
        "model_probability_percent": round(model_p * 100, 1),
        "expected_value_percent": ev,
        "expected_value_label": f"{ev:+.1f}%",
        "risk": risk,
        "kelly_stake_percent": kelly,
        "kelly_suggested": _kelly_bucket(kelly),
        "edge": val > 2.0,
    }


def _kelly_bucket(kelly_pct: float) -> str:
    if kelly_pct >= 4.0:
        return "5%"
    if kelly_pct >= 2.0:
        return "2%"
    if kelly_pct >= 1.0:
        return "1%"
    if kelly_pct >= 0.5:
        return "0.5%"
    return "0.5%"
