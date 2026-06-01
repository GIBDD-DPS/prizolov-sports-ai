import unittest

from fastapi.testclient import TestClient

from app.main import LIVE_EVENTS, app


class TestWidgetApiContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_get_ai_sports_returns_events_for_get_all(self):
        response = self.client.post("/get-ai-sports.php", json={"get_all": True})
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertIn("events", payload)
        self.assertIn("total", payload)
        self.assertEqual(payload["total"], len(LIVE_EVENTS))
        self.assertIsInstance(payload["events"], list)
        self.assertGreater(len(payload["events"]), 0)

    def test_get_ai_sports_supports_event_index(self):
        requested_index = len(LIVE_EVENTS) + 2
        expected_index = requested_index % len(LIVE_EVENTS)
        expected_event = LIVE_EVENTS[expected_index]

        response = self.client.post(
            "/get-ai-sports.php",
            json={"event_index": requested_index},
        )
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertIn("match_info", payload)
        self.assertIn("recommendations", payload)
        self.assertEqual(payload["event_index"], expected_index)
        self.assertEqual(payload["total_events"], len(LIVE_EVENTS))
        self.assertEqual(payload["match_info"]["home"], expected_event["home"])
        self.assertEqual(payload["match_info"]["away"], expected_event["away"])
        self.assertIsInstance(payload["recommendations"], list)


if __name__ == "__main__":
    unittest.main()
