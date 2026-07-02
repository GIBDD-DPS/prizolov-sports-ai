# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.40 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Regression tests for production FastAPI route registration."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("PARSER_ENABLED", "false")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.main import app  # noqa: E402


class MainRouteRegistrationTest(unittest.TestCase):
    def test_api_routes_are_registered_under_v1_prefix(self) -> None:
        route_paths = set(app.openapi()["paths"])

        self.assertTrue(
            {
                "/api/v1/health",
                "/api/v1/sports",
                "/api/v1/events",
                "/api/v1/events/{event_id}",
                "/api/v1/predictions",
                "/api/v1/admin/parse",
                "/api/v1/storefront-widget",
            }.issubset(route_paths)
        )

    def test_static_storefront_mount_is_registered(self) -> None:
        self.assertTrue(
            any(getattr(route, "name", "") == "static" for route in app.routes),
            "backend/static must remain mounted for same-origin storefront hosting",
        )


if __name__ == "__main__":
    unittest.main()
