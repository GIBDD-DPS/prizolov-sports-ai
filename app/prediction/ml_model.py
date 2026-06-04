# LightGBM / sklearn probabilistic 1X2 model.

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

logger = logging.getLogger("PrizolovSportsAI.PredictionML")

_MODEL = None
_MODEL_PATH = Path(os.getenv("PREDICTION_MODEL_PATH", "runtime/prediction_lgbm.joblib"))


def _feature_vector(event: Dict[str, Any], context: Dict[str, Any]) -> List[float]:
    xg = context.get("xg_profile") or {}
    cal = context.get("calendar") or {}
    lineup = context.get("lineup") or {}
    mot = context.get("motivation") or {}
    from prediction.elo import get_elo

    home = str(event.get("home") or "")
    away = str(event.get("away") or "")
    return [
        get_elo(home),
        get_elo(away),
        float(xg.get("xg_home") or 1.3),
        float(xg.get("xg_away") or 1.1),
        float(cal.get("home_calendar_score") or 0.5),
        float(cal.get("away_calendar_score") or 0.5),
        float(lineup.get("confidence_multiplier") or 1.0),
        float(mot.get("home_motivation") or 0.5),
        float(mot.get("away_motivation") or 0.5),
        1.0 if event.get("is_live") else 0.0,
    ]


def _heuristic_1x2(features: List[float]) -> Dict[str, float]:
    elo_h, elo_a = features[0], features[1]
    xg_h, xg_a = features[2], features[3]
    from prediction.elo import expected_score

    p_h = expected_score(elo_h + 50, elo_a)
    p_a = expected_score(elo_a, elo_h + 50)
    xg_ratio = xg_h / max(0.2, xg_h + xg_a)
    blend_h = 0.6 * p_h + 0.4 * xg_ratio
    blend_a = 0.6 * p_a + 0.4 * (1 - xg_ratio)
    d = 0.24
    s = 1 - d
    t = blend_h + blend_a or 1
    return {
        "home_win": round(s * blend_h / t, 4),
        "draw": d,
        "away_win": round(s * blend_a / t, 4),
    }


def _load_model():
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    if _MODEL_PATH.exists():
        try:
            import joblib

            _MODEL = joblib.load(_MODEL_PATH)
            return _MODEL
        except Exception as exc:
            logger.warning("ML model load failed: %s", exc)
    return None


def predict_1x2_ml(event: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, float]:
    features = _feature_vector(event, context)
    model = _load_model()
    if model is None:
        return _heuristic_1x2(features)

    try:
        X = np.array([features])
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(X)[0]
            if proba.shape[0] >= 3:
                return {
                    "home_win": round(float(proba[0]), 4),
                    "draw": round(float(proba[1]), 4),
                    "away_win": round(float(proba[2]), 4),
                }
        pred = model.predict(X)
        if hasattr(pred, "__iter__"):
            p = list(pred)[0]
            if isinstance(p, dict):
                return p
    except Exception as exc:
        logger.warning("ML predict failed: %s", exc)
    return _heuristic_1x2(features)


def train_bootstrap_model(samples: int = 800) -> bool:
    """Train a small LightGBM on synthetic data for cold-start deployment."""
    try:
        import joblib
        from sklearn.model_selection import train_test_split
        from lightgbm import LGBMClassifier
    except ImportError:
        logger.info("LightGBM/sklearn not available for bootstrap train")
        return False

    rng = np.random.default_rng(42)
    X = rng.normal(size=(samples, 10))
    y = rng.integers(0, 3, size=samples)
    clf = LGBMClassifier(
        n_estimators=80,
        max_depth=5,
        learning_rate=0.08,
        objective="multiclass",
        num_class=3,
        verbose=-1,
    )
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)
    clf.fit(Xtr, ytr)
    _MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, _MODEL_PATH)
    global _MODEL
    _MODEL = clf
    return True
