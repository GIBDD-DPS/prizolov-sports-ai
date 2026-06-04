# Bet result tracker — accuracy, profit, Brier after each settled event.

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from core.metrics import metrics as formulas
from core.metrics.store import append_bet, append_brier, load, update_totals


def record_prediction_bet(
    *,
    match: str,
    prediction: str,
    odds: float,
    probability: float,
    stake: float = 1.0,
    market: str = "",
    league: str = "",
    sport: str = "football",
    opening_odds: Optional[float] = None,
) -> Dict[str, Any]:
    record = {
        "ts": time.time(),
        "match": match,
        "prediction": prediction,
        "odds": round(float(odds), 3),
        "opening_odds": round(float(opening_odds or odds), 3),
        "closing_odds": None,
        "probability": round(float(probability), 4),
        "stake": round(float(stake), 2),
        "result": "open",
        "profit": 0.0,
        "market": market,
        "league": league,
        "sport": sport,
    }
    append_bet(record)
    update_totals(predictions=1)
    return record


def settle_bet(
    *,
    match: str,
    prediction: str,
    result: str,
    profit: Optional[float] = None,
    closing_odds: Optional[float] = None,
    outcome_binary: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """
    result: WIN | LOSS | PUSH | VOID
    outcome_binary: 1/0 for Brier (auto from result if omitted)
    """
    state = load()
    bets: List[Dict[str, Any]] = list(state.get("bets") or [])
    updated = None
    for bet in reversed(bets):
        if bet.get("match") == match and bet.get("prediction") == prediction and bet.get("result") == "open":
            res = result.upper()
            bet["result"] = res
            if closing_odds is not None:
                bet["closing_odds"] = round(float(closing_odds), 3)
            if profit is not None:
                bet["profit"] = round(float(profit), 3)
            elif res == "WIN":
                bet["profit"] = round(bet["stake"] * (bet["odds"] - 1.0), 3)
            elif res == "LOSS":
                bet["profit"] = round(-bet["stake"], 3)
            else:
                bet["profit"] = 0.0
            bet["settled_ts"] = time.time()
            updated = bet
            break

    if not updated:
        return None

    state["bets"] = bets
    from core.metrics.store import save

    save(state)

    ob = outcome_binary
    if ob is None:
        ob = 1 if updated["result"] == "WIN" else 0
    brier = formulas.brier_score(updated["probability"], ob)
    append_brier({"ts": time.time(), "match": match, "brier": brier, "probability": updated["probability"]})

    delta = {"wins": 0, "losses": 0, "push": 0, "void": 0, "stake_total": updated["stake"], "profit_total": updated["profit"]}
    r = updated["result"]
    if r == "WIN":
        delta["wins"] = 1
    elif r == "LOSS":
        delta["losses"] = 1
    elif r == "PUSH":
        delta["push"] = 1
    else:
        delta["void"] = 1
    update_totals(**delta)
    return updated


def accuracy_summary() -> Dict[str, Any]:
    state = load()
    totals = dict(state.get("totals") or {})
    wins = int(totals.get("wins") or 0)
    losses = int(totals.get("losses") or 0)
    push = int(totals.get("push") or 0)
    void = int(totals.get("void") or 0)
    total = int(totals.get("predictions") or 0)
    settled = wins + losses
    return {
        "predictions_total": total,
        "wins": wins,
        "losses": losses,
        "push": push,
        "void": void,
        "win_rate": formulas.win_rate(wins, settled + push + void, push=push, void=void),
        "settled": settled,
    }


def brier_summary(*, limit: int = 200) -> Dict[str, Any]:
    state = load()
    hist = list(state.get("brier_history") or [])[-limit:]
    if not hist:
        return {"samples": 0, "avg_brier": 0.0, "recent": []}
    avg = sum(h.get("brier", 0) for h in hist) / len(hist)
    return {"samples": len(hist), "avg_brier": round(avg, 4), "recent": hist[-20:]}
