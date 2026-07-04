# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.40 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Smoke tests for production FastAPI route wiring."""

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))


class FastAPIWiringTest(unittest.TestCase):
    def test_production_app_registers_api_routes(self) -> None:
        from app.main import app

        registered_paths = set(app.openapi()["paths"])

        self.assertIn("/api/v1/health", registered_paths)
        self.assertIn("/api/v1/sports", registered_paths)
        self.assertIn("/api/v1/events", registered_paths)
        self.assertIn("/api/v1/predictions", registered_paths)
        self.assertIn("/api/v1/admin/parse", registered_paths)
        self.assertIn("/api/v1/storefront-widget", registered_paths)


if __name__ == "__main__":
    unittest.main()
