# ============================================
# Prizolov Sports AI - Setup
# Version: 4.01 (Social Sentiment & Global AI Upgrade)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Text
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей проекта"""
    pass

class Prediction(Base):
    """
    Модель хранения прогнозов.
    Полностью соответствует формату вывода для сайта:
    команды, время начала, сколько прошло, коэффициент, прогноз, 
    вероятность (%), рекомендуемая ставка, EV, уверенность.
    """
    __tablename__ = "predictions"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    match_id = Column(String, unique=True, index=True, nullable=False, comment="Уникальный ID матча от источников")
    
    # Информация о матче
    home_team = Column(String, nullable=False)
    away_team = Column(String, nullable=False)
    sport_type = Column(String, nullable=False, comment="football, hockey, basketball, etc.")
    league = Column(String, nullable=True)
    start_time = Column(DateTime, nullable=True, comment="Время начала матча (UTC)")
    status = Column(String, nullable=False, default="upcoming", comment="upcoming, live, finished")
    current_minute = Column(Integer, nullable=True, comment="Сколько прошло (минута для live-матчей)")
    
    # Коэффициенты букмекеров
    odds = Column(JSON, nullable=True, comment="{'1': 1.85, 'X': 3.50, '2': 4.10, 'total_over': 1.95}")
    
    # Прогноз и метрики
    prediction_outcome = Column(String, nullable=False, comment="П1, П2, X, 1X, 2X, ТБ/ТМ")
    probability = Column(Float, nullable=False, comment="Вероятность исхода в процентах (0.0 - 100.0)")
    recommended_bet = Column(Text, nullable=False, comment="Рекомендуемая ставка для сайта")
    expected_value = Column(Float, nullable=False, comment="Expected Value (EV) > 0 указывает на value-ставку")
    confidence = Column(String, nullable=False, comment="Уверенность: High, Med, Low")
    
    # Технические поля
    layers_output = Column(JSON, nullable=True, comment="Отладочный вывод слоёв: stat, ml, ai_sentiment")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
