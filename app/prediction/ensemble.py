# Ensemble: Model 40%, Market 25%, xG 15%, Form 10%, News 10%.

from __future__ import annotations

from typing import Any, Dict

from prediction.agents import form_agent, market_agent, model_agent, news_agent, xg_agent

WEIGHTS = {
    "model": 0.40,
    "market": 0.25,
    "xg": 0.15,
    "form": 0.10,
    "news": 0.10,
}


def _normalize(probs: Dict[str, float]) -> Dict[str, float]:
    h = float(probs.get("home_win") or 0)
    d = float(probs.get("draw") or 0)
    a = float(probs.get("away_win") or 0)
    t = h + d + a
    if t <= 0:
        return {"home_win": 0.33, "draw": 0.34, "away_win": 0.33}
    return {
        "home_win": round(h / t, 4),
        "draw": round(d / t, 4),
        "away_win": round(a / t, 4),
    }


def combine_ensemble(event: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    agents = {
        "model": model_agent.run(event, context),
        "market": market_agent.run(event, context),
        "xg": xg_agent.run(event, context),
        "form": form_agent.run(event, context),
        "news": news_agent.run(event, context),
    }
    out = {"home_win": 0.0, "draw": 0.0, "away_win": 0.0}
    for name, weight in WEIGHTS.items():
        p = agents[name]
        out["home_win"] += weight * float(p.get("home_win") or 0)
        out["draw"] += weight * float(p.get("draw") or 0)
        out["away_win"] += weight * float(p.get("away_win") or 0)
    final = _normalize(out)
    return {
        "probabilities": final,
        "agents": agents,
        "weights": WEIGHTS,
    }
