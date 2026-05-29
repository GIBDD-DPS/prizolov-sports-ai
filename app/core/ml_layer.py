# ============================================
# Prizolov Sports AI - Setup
# Version: 4.01 (Social Sentiment & Global AI Upgrade)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

import asyncio
import structlog
import joblib
import pandas as pd
from typing import Dict, Any
from pathlib import Path

log = structlog.get_logger()

class MLPredictor:
    """
    ML-слой прогнозирования.
    Загружает обученную модель (LightGBM/XGBoost) и генерирует вероятности
    на основе признаков матча, коэффициентов и статистического базиса.
    Использует asyncio.to_thread для неблокирующих CPU-вычислений.
    """
    def __init__(self, model_path: str = "models/predictor_v401.joblib"):
        self.model_path = Path(model_path)
        self.model = None
        self.feature_names = [
            "odds_1_inv", "odds_X_inv", "odds_2_inv", "stat_home",
            "stat_draw", "stat_away", "bookmaker_margin", "is_live", "league_weight"
        ]
        self.load_model()

    def load_model(self):
        """Загрузка сериализованной модели из файла"""
        if not self.model_path.exists():
            log.warning("ML model file not found, will fallback to statistical layer", path=str(self.model_path))
            return
        try:
            self.model = joblib.load(self.model_path)
            log.info("ML model loaded successfully")
        except Exception as e:
            log.error("Failed to load ML model", error=str(e))
            self.model = None

    def _prepare_features(self, match_data: Dict[str, Any], stat_probs: Dict[str, float]) -> pd.DataFrame:
        """Формирование вектора признаков для модели"""
        odds = match_data.get("odds", {})
        o1 = float(odds.get("1", 2.0) or 2.0)
        oX = float(odds.get("X", 3.5) or 3.5)
        o2 = float(odds.get("2", 2.0) or 2.0)

        margin = (1/o1 + 1/oX + 1/o2) - 1.0
        is_live = 1.0 if match_data.get("current_minute") and match_data["current_minute"] > 0 else 0.0

        row = {
            "odds_1_inv": 1.0 / o1 if o1 > 1 else 0.5,
            "odds_X_inv": 1.0 / oX if oX > 1 else 0.25,
            "odds_2_inv": 1.0 / o2 if o2 > 1 else 0.5,
            "stat_home": stat_probs.get("home_win", 0.33),
            "stat_draw": stat_probs.get("draw", 0.33),
            "stat_away": stat_probs.get("away_win", 0.33),
            "bookmaker_margin": margin,
            "is_live": is_live,
            "league_weight": 1.0  # Placeholder: в продакшене маппится на вес лиги из БД
        }
        return pd.DataFrame([row])[self.feature_names]

    def _predict_sync(self, features: pd.DataFrame) -> Dict[str, float]:
        """Синхронный вызов модели (выполняется в отдельном потоке)"""
        if self.model is None:
            raise RuntimeError("Model not loaded")
        # predict_proba возвращает массив [away, draw, home] при стандартном encoding 0/1/2
        probs = self.model.predict_proba(features)[0]
        return {
            "away_win": float(probs[0]),
            "draw": float(probs[1]),
            "home_win": float(probs[2])
        }

    async def predict(self, match_data: Dict[str, Any], stat_probs: Dict[str, float]) -> Dict[str, float]:
        """Асинхронная обертка для ML-предсказания"""
        if self.model is None:
            log.info("ML layer skipped (no model), returning stat baseline")
            return stat_probs

        try:
            features = self._prepare_features(match_data, stat_probs)
            # Выносим CPU-задачу в пул потоков, чтобы не блокировать asyncio event loop
            return await asyncio.to_thread(self._predict_sync, features)
        except Exception as e:
            log.error("ML prediction failed", match_id=match_data.get("match_id"), error=str(e))
            return stat_probs

# Глобальный экземпляр для переиспользования в рамках процесса
predictor = MLPredictor()

async def predict_with_ml(match_data: Dict[str, Any], stat_probs: Dict[str, float]) -> Dict[str, float]:
    """Публичная точка входа для prediction_engine"""
    return await predictor.predict(match_data, stat_probs)
