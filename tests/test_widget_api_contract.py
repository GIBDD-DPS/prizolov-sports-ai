import os
import unittest
from pathlib import Path

os.environ.setdefault("SELF_LEARNING_STATE_PATH", "/tmp/prizolov_self_learning_state_test.json")
os.environ.setdefault("SELF_LEARNING_MIN_FEEDBACK", "3")

# Чистим test-state до импорта приложения, чтобы тесты были детерминированы.
_test_state_path = Path(os.environ["SELF_LEARNING_STATE_PATH"])
if _test_state_path.exists():
    _test_state_path.unlink()

from fastapi.testclient import TestClient

from app.main import app


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
        self.assertEqual(payload["total"], len(payload["events"]))
        self.assertIsInstance(payload["events"], list)
        self.assertGreater(len(payload["events"]), 0)

    def test_get_ai_sports_supports_event_index(self):
        all_events_response = self.client.post("/get-ai-sports.php", json={"get_all": True})
        all_events_payload = all_events_response.json()
        self.assertGreater(all_events_payload["total"], 0)

        requested_index = all_events_payload["total"] + 2
        expected_index = requested_index % all_events_payload["total"]
        expected_event = all_events_payload["events"][expected_index]

        response = self.client.post(
            "/get-ai-sports.php",
            json={"event_index": requested_index},
        )
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertIn("match_info", payload)
        self.assertIn("recommendations", payload)
        self.assertEqual(payload["event_index"], expected_index)
        self.assertEqual(payload["total_events"], all_events_payload["total"])
        self.assertEqual(payload["match_info"]["home"], expected_event["home"])
        self.assertEqual(payload["match_info"]["away"], expected_event["away"])
        self.assertIsInstance(payload["recommendations"], list)

    def test_self_learning_feedback_calibrates_probabilities(self):
        all_events_response = self.client.get("/api/all-events?lang=en")
        self.assertEqual(all_events_response.status_code, 200)
        events_payload = all_events_response.json()
        self.assertGreater(events_payload.get("total", 0), 0)

        events = events_payload.get("events", [])
        chosen_sport = None
        chosen_rec = None
        for event in events:
            recommendations = event.get("recommendations") or []
            if recommendations:
                chosen_sport = event.get("sport_code") or event.get("sport")
                chosen_rec = recommendations[0]
                break

        self.assertIsNotNone(chosen_sport)
        self.assertIsNotNone(chosen_rec)

        for _ in range(4):
            feedback_response = self.client.post(
                "/api/learning/feedback",
                json={
                    "sport": chosen_sport,
                    "predicted_probability": 0.45,
                    "outcome": True,
                },
            )
            self.assertEqual(feedback_response.status_code, 200)

        learning_status_response = self.client.get("/api/learning/status")
        self.assertEqual(learning_status_response.status_code, 200)
        learning_status = learning_status_response.json()

        self.assertIn("sports", learning_status)
        self.assertIn(chosen_sport, learning_status["sports"])

        sport_stats = learning_status["sports"][chosen_sport]
        self.assertGreaterEqual(sport_stats.get("feedback_count", 0), 4)
        self.assertGreater(sport_stats.get("factor", 1.0), 1.0)

        calibrated_events_response = self.client.get(f"/api/events/{chosen_sport}?lang=en")
        self.assertEqual(calibrated_events_response.status_code, 200)
        calibrated_events = calibrated_events_response.json().get("events", [])

        calibrated_rec = None
        for event in calibrated_events:
            recommendations = event.get("recommendations") or []
            if recommendations:
                calibrated_rec = recommendations[0]
                break

        self.assertIsNotNone(calibrated_rec)
        self.assertIn("base_probability", calibrated_rec)
        self.assertIn("learning_factor", calibrated_rec)
        self.assertGreaterEqual(
            calibrated_rec["probability"],
            calibrated_rec["base_probability"],
        )


if __name__ == "__main__":
    unittest.main()
