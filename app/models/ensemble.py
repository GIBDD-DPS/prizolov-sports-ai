# ML ensemble: LightGBM + XGBoost + CatBoost (optional) → 1X2.

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger("PrizolovSportsAI.MLEnsemble")

_MODELS: Dict[str, Any] = {}


def _feature_vector(features: Dict[str, Any]) -> List[float]:
    r = features.get("ratings") or features
    elo = r.get("elo_rating") or {}
    xg = r.get("xg_rating") or {}
    form = r.get("form_rating") or {}
    fat = r.get("schedule_fatigue_rating") or {}
    return [
        float(elo.get("home") or 1500),
        float(elo.get("away") or 1500),
        float(xg.get("offensive_home") or 1.3),
        float(xg.get("defensive_home") or 1.2),
        float(xg.get("offensive_away") or 1.1),
        float(xg.get("defensive_away") or 1.3),
        float(form.get("home") or 0.5),
        float(form.get("away") or 0.5),
        float(fat.get("home") or 0.5),
        float(fat.get("away") or 0.5),
    ]


def _predict_one(model: Any, X: np.ndarray) -> Optional[Dict[str, float]]:
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(X)[0]
        if len(proba) >= 3:
            return {
                "home_win": float(proba[0]),
                "draw": float(proba[1]),
                "away_win": float(proba[2]),
            }
    return None


def _load_models() -> Dict[str, Any]:
    global _MODELS
    if _MODELS:
        return _MODELS
    try:
        from prediction.ml_model import _load_model

        lgb = _load_model()
        if lgb:
            _MODELS["lightgbm"] = lgb
    except Exception as exc:
        logger.debug("LightGBM skip: %s", exc)
    try:
        import joblib
        from pathlib import Path
        import os

        xgb_path = Path(os.getenv("XGB_MODEL_PATH", "runtime/prediction_xgb.joblib"))
        if xgb_path.exists():
            _MODELS["xgboost"] = joblib.load(xgb_path)
    except Exception:
        pass
    try:
        import joblib
        from pathlib import Path
        import os

        cb_path = Path(os.getenv("CATBOOST_MODEL_PATH", "runtime/prediction_catboost.joblib"))
        if cb_path.exists():
            _MODELS["catboost"] = joblib.load(cb_path)
    except Exception:
        pass
    return _MODELS


def predict_ensemble(features: Dict[str, Any]) -> Dict[str, Any]:
    from core.system_monitor.latency import track_stage
    from prediction.ml_model import _heuristic_1x2

    with track_stage("ml_model"):
        X = np.array([_feature_vector(features)])
        models = _load_models()
        preds: List[Dict[str, float]] = []
        for name, model in models.items():
            p = _predict_one(model, X)
            if p:
                preds.append(p)
        if not preds:
            h = _heuristic_1x2(_feature_vector(features))
            return {"probabilities": h, "models_used": ["heuristic"], "weights": {"heuristic": 1.0}}

        out = {"home_win": 0.0, "draw": 0.0, "away_win": 0.0}
        w = 1.0 / len(preds)
        for p in preds:
            out["home_win"] += w * p["home_win"]
            out["draw"] += w * p["draw"]
            out["away_win"] += w * p["away_win"]
        t = out["home_win"] + out["draw"] + out["away_win"] or 1.0
        probs = {k: round(v / t, 4) for k, v in out.items()}
        return {
            "probabilities": probs,
            "models_used": list(models.keys()),
            "weights": {k: round(w, 3) for k in models},
        }
