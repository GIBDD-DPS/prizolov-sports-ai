# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.40 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Regression tests for FastAPI route registration."""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.main import app  # noqa: E402


class AppWiringTest(unittest.TestCase):
    def test_public_api_routes_are_registered(self) -> None:
        paths = set(app.openapi()["paths"])

        self.assertIn("/api/v1/health", paths)
        self.assertIn("/api/v1/sports", paths)
        self.assertIn("/api/v1/events", paths)
        self.assertIn("/api/v1/events/{event_id}", paths)
        self.assertIn("/api/v1/predictions", paths)
        self.assertIn("/api/v1/admin/parse", paths)
        self.assertIn("/api/v1/storefront-widget", paths)

    def test_static_frontend_is_mounted_after_api_routes(self) -> None:
        route_names = [getattr(route, "name", "") for route in app.routes]

        self.assertIn("static", route_names)
        self.assertLess(
            route_names.index("storefront_widget"),
            route_names.index("static"),
        )


if __name__ == "__main__":
    unittest.main()
