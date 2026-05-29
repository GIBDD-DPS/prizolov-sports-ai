# ============================================
# Prizolov Sports AI - Setup
# Version: 4.01 (Social Sentiment & Global AI Upgrade)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class PredictionResponse(BaseModel):
    """
    Схема ответа API для фронтенда prizolov.ru.
    Содержит все запрошенные метрики в строгой типизации.
    """
    match_id: str = Field(..., description="Уникальный идентификатор матча")
    home_team: str = Field(..., description="Команда хозяев")
    away_team: str = Field(..., description="Команда гостей")
    sport_type: str = Field(..., description="Вид спорта")
    league: Optional[str] = Field(None, description="Лига или чемпионат")
    start_time: Optional[datetime] = Field(None, description="Время начала матча")
    current_minute: Optional[int] = Field(None, description="Сколько прошло (минута)")
    odds: Optional[dict] = Field(None, description="Текущие коэффициенты (1/X/2 и др.)")
    prediction_outcome: str = Field(..., description="Прогноз (исход)")
    probability: float = Field(..., ge=0.0, le=100.0, description="Вероятность исхода (%)")
    recommended_bet: str = Field(..., description="Рекомендуемая ставка")
    expected_value: float = Field(..., description="Expected Value (EV)")
    confidence: str = Field(..., pattern="^(High|Med|Low)$", description="Уверенность (High/Med/Low)")

    class Config:
        from_attributes = True  # Совместимость с SQLAlchemy ORM (Pydantic V2)
