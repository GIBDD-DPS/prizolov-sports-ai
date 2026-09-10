# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.18 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Add accuracy_log table for prediction vs actual outcome reconciliation."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_accuracy_log"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "accuracy_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id"), nullable=False),
        sa.Column("market_id", sa.Integer(), sa.ForeignKey("markets.id"), nullable=False),
        sa.Column(
            "prediction_id", sa.Integer(), sa.ForeignKey("predictions.id"), nullable=False
        ),
        sa.Column("predicted_selection", sa.String(length=32), nullable=False),
        sa.Column("predicted_probability", sa.Float(), nullable=False),
        sa.Column("actual_selection", sa.String(length=32), nullable=False),
        sa.Column("correct", sa.Boolean(), nullable=False),
        sa.Column("brier_score", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_accuracy_log_event_id", "accuracy_log", ["event_id"])
    op.create_index("ix_accuracy_log_market_id", "accuracy_log", ["market_id"])
    op.create_index("ix_accuracy_log_prediction_id", "accuracy_log", ["prediction_id"])


def downgrade() -> None:
    op.drop_index("ix_accuracy_log_prediction_id", table_name="accuracy_log")
    op.drop_index("ix_accuracy_log_market_id", table_name="accuracy_log")
    op.drop_index("ix_accuracy_log_event_id", table_name="accuracy_log")
    op.drop_table("accuracy_log")
