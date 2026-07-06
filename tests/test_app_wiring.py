"""Regression tests for the deployed FastAPI entrypoint wiring."""

from __future__ import annotations

import asyncio
import importlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

main = importlib.import_module("app.main")


class AppWiringTest(unittest.TestCase):
    def test_api_routes_are_registered_under_configured_prefix(self) -> None:
        paths = set(main.app.openapi()["paths"])

        expected = {
            "/api/v1/health",
            "/api/v1/sports",
            "/api/v1/events",
            "/api/v1/events/{event_id}",
            "/api/v1/predictions",
            "/api/v1/admin/parse",
            "/api/v1/storefront-widget",
        }

        self.assertTrue(expected.issubset(paths))

    def test_static_storefront_is_mounted_after_api_routes(self) -> None:
        route_names = [getattr(route, "name", None) for route in main.app.routes]
        self.assertIn("static", route_names)

        static_index = route_names.index("static")
        api_indexes = [
            index
            for index, route in enumerate(main.app.routes)
            if getattr(route, "path", "").startswith("/api/v1")
        ]

        self.assertTrue(api_indexes)
        self.assertLess(max(api_indexes), static_index)

    def test_lifespan_starts_and_cancels_scheduler(self) -> None:
        class DummyTask:
            def __init__(self) -> None:
                self.cancelled = False

            def done(self) -> bool:
                return False

            def cancel(self) -> None:
                self.cancelled = True

        task = DummyTask()

        async def run_lifespan() -> None:
            async with main.lifespan(main.app):
                pass

        with patch.object(main, "start_parser_scheduler", return_value=task) as start:
            asyncio.run(run_lifespan())

        start.assert_called_once_with()
        self.assertTrue(task.cancelled)


if __name__ == "__main__":
    unittest.main()
