# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.40 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Odds(Base):
    __tablename__ = "odds"
    __table_args__ = (
        UniqueConstraint(
            "market_id", "source_id", "selection", name="uq_odds_source_selection"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    market_id: Mapped[int] = mapped_column(ForeignKey("markets.id"), index=True)
    source_id: Mapped[str] = mapped_column(String(32), index=True)
    selection: Mapped[str] = mapped_column(String(32))
    odds_value: Mapped[float | None] = mapped_column(Float)
    implied_prob: Mapped[float | None] = mapped_column(Float)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    market: Mapped["Market"] = relationship(back_populates="odds")
