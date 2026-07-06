# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.40 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

from __future__ import annotations

from sqlalchemy import Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Market(Base):
    __tablename__ = "markets"
    __table_args__ = (
        UniqueConstraint("event_id", "market_type", "line_value", name="uq_market_line"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), index=True)
    market_type: Mapped[str] = mapped_column(String(32), index=True)
    line_value: Mapped[float | None] = mapped_column(Float)

    event: Mapped["Event"] = relationship(back_populates="markets")
    odds: Mapped[list["Odds"]] = relationship(
        back_populates="market", cascade="all, delete-orphan"
    )
    predictions: Mapped[list["Prediction"]] = relationship(back_populates="market")
