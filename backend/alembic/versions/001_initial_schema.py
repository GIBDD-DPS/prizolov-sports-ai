# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.14 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Initial database schema and seed data."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_sports_slug", "sports", ["slug"], unique=True)

    op.create_table(
        "parse_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("base_url", sa.String(length=512), nullable=False),
        sa.Column("sport_id", sa.Integer(), sa.ForeignKey("sports.id"), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_ok_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
    )
    op.create_index("ix_parse_sources_source_id", "parse_sources", ["source_id"], unique=True)

    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sport_id", sa.Integer(), sa.ForeignKey("sports.id"), nullable=False),
        sa.Column("home_team", sa.String(length=128), nullable=False),
        sa.Column("away_team", sa.String(length=128), nullable=False),
        sa.Column("league", sa.String(length=128), nullable=False, server_default=""),
        sa.Column("kickoff_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="scheduled"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "sport_id", "home_team", "away_team", "kickoff_at", name="uq_event_match"
        ),
    )
    op.create_index("ix_events_sport_id", "events", ["sport_id"])
    op.create_index("ix_events_kickoff_at", "events", ["kickoff_at"])

    op.create_table(
        "markets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id"), nullable=False),
        sa.Column("market_type", sa.String(length=32), nullable=False),
        sa.Column("line_value", sa.Float()),
        sa.UniqueConstraint("event_id", "market_type", "line_value", name="uq_market_line"),
    )
    op.create_index("ix_markets_event_id", "markets", ["event_id"])
    op.create_index("ix_markets_market_type", "markets", ["market_type"])

    op.create_table(
        "odds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("market_id", sa.Integer(), sa.ForeignKey("markets.id"), nullable=False),
        sa.Column("source_id", sa.String(length=32), nullable=False),
        sa.Column("selection", sa.String(length=32), nullable=False),
        sa.Column("odds_value", sa.Float()),
        sa.Column("implied_prob", sa.Float()),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "market_id", "source_id", "selection", name="uq_odds_source_selection"
        ),
    )
    op.create_index("ix_odds_market_id", "odds", ["market_id"])
    op.create_index("ix_odds_source_id", "odds", ["source_id"])

    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id"), nullable=False),
        sa.Column("market_id", sa.Integer(), sa.ForeignKey("markets.id"), nullable=False),
        sa.Column("selection", sa.String(length=32), nullable=False),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("confidence", sa.String(length=16), nullable=False, server_default="medium"),
        sa.Column("factors", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_predictions_event_id", "predictions", ["event_id"])
    op.create_index("ix_predictions_market_id", "predictions", ["market_id"])

    op.create_table(
        "parse_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("items_fetched", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("message", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_parse_logs_source_id", "parse_logs", ["source_id"])

    sports = sa.table(
        "sports",
        sa.column("id", sa.Integer),
        sa.column("slug", sa.String),
        sa.column("name", sa.String),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(
        sports,
        [
            {"id": 1, "slug": "football", "name": "Футбол", "is_active": True},
            {"id": 2, "slug": "hockey", "name": "Хоккей", "is_active": False},
            {"id": 3, "slug": "basketball", "name": "Баскетбол", "is_active": False},
        ],
    )

    sources = sa.table(
        "parse_sources",
        sa.column("source_id", sa.String),
        sa.column("name", sa.String),
        sa.column("base_url", sa.String),
        sa.column("sport_id", sa.Integer),
        sa.column("is_enabled", sa.Boolean),
    )
    op.bulk_insert(
        sources,
        [
            {
                "source_id": "forebet",
                "name": "Forebet",
                "base_url": "https://www.forebet.com",
                "sport_id": 1,
                "is_enabled": True,
            },
            {
                "source_id": "predictz",
                "name": "Predictz",
                "base_url": "https://www.predictz.com/predictions/",
                "sport_id": 1,
                "is_enabled": True,
            },
            {
                "source_id": "betensured",
                "name": "Betensured RU",
                "base_url": "https://ru.betensured.com",
                "sport_id": 1,
                "is_enabled": True,
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("parse_logs")
    op.drop_table("predictions")
    op.drop_table("odds")
    op.drop_table("markets")
    op.drop_table("events")
    op.drop_table("parse_sources")
    op.drop_table("sports")
