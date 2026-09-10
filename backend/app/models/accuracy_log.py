# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.18 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""История сверки прогнозов с фактическими исходами матчей."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AccuracyLog(Base):
    __tablename__ = "accuracy_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), index=True)
    market_id: Mapped[int] = mapped_column(ForeignKey("markets.id"), index=True)
    prediction_id: Mapped[int] = mapped_column(ForeignKey("predictions.id"), index=True)

    predicted_selection: Mapped[str] = mapped_column(String(32))
    predicted_probability: Mapped[float] = mapped_column(Float)
    actual_selection: Mapped[str] = mapped_column(String(32))
    correct: Mapped[bool] = mapped_column(Boolean)

    # Brier score по трём классам (1/X/2): сумма (p_i - y_i)^2 по всем исходам,
    # где y_i = 1 для реально случившегося исхода, иначе 0.
    # 0.0 = идеальный прогноз, 2.0 = наихудший возможный.
    brier_score: Mapped[float] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    event: Mapped["Event"] = relationship()
    market: Mapped["Market"] = relationship()
    prediction: Mapped["Prediction"] = relationship()
