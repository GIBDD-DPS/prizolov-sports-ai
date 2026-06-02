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


    def test_source_status_exposes_quality_filters(self):
        response = self.client.get("/api/source-status")
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertIn("quality_filters", payload)
        quality = payload["quality_filters"]
        self.assertIn("supported_runtime_sports", quality)
        self.assertIn("min_bookmakers_per_event", quality)
        self.assertIn("min_recommendation_probability", quality)
        self.assertIn("min_event_quality_score", quality)
        self.assertIn("max_recommendations_per_event", quality)
        self.assertIn("effective_min_recommendation_probability", quality)
        self.assertIn("adaptive_threshold_enabled", quality)

        self.assertIn("self_learning", payload)
        self.assertIn("enabled", payload["self_learning"])
        self.assertIn("storefront_policy", payload)
        self.assertIn("mode", payload["storefront_policy"])

    def test_all_events_supports_filters_and_top_recommendations(self):
        response = self.client.get(
            "/api/all-events?lang=en&sport=football&min_probability=0.6&sort_by=priority&limit=3"
        )
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertIn("filters", payload)
        self.assertIn("meta", payload)
        self.assertIn("top_recommendations", payload)
        self.assertIn("storefront_policy", payload)
        self.assertIn("requested", payload["filters"])
        self.assertIn("effective", payload["filters"])
        self.assertLessEqual(payload["total"], 3)

        effective_min_probability = payload["filters"]["effective"].get("min_probability", 0.0)

        for event in payload.get("events", []):
            self.assertEqual(event.get("sport_code"), "football")
            top_probability = event.get("top_probability")
            if top_probability is not None:
                self.assertGreaterEqual(float(top_probability), float(effective_min_probability))

    def test_top_recommendations_endpoint(self):
        response = self.client.get("/api/recommendations/top?lang=en&limit=5&min_probability=0.5")
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertIn("recommendations", payload)
        self.assertIn("storefront_policy", payload)
        self.assertIn("filters", payload)
        self.assertIn("effective", payload["filters"])
        self.assertLessEqual(payload.get("total", 0), 5)

        effective_min_probability = payload["filters"]["effective"].get("min_probability", 0.0)

        for rec in payload.get("recommendations", []):
            self.assertIn("event_id", rec)
            self.assertIn("line", rec)
            self.assertIn("probability", rec)
            self.assertGreaterEqual(float(rec["probability"]), float(effective_min_probability))


    def test_learning_metrics_endpoint_returns_summary_and_recent_feedback(self):
        feedback_response = self.client.post(
            "/api/learning/feedback",
            json={
                "sport": "football",
                "predicted_probability": 0.62,
                "outcome": True,
                "coefficient": 1.9,
                "event_id": "test_event_1",
                "line": "H2H: Team A",
                "source": "unit_test",
            },
        )
        self.assertEqual(feedback_response.status_code, 200)

        metrics_response = self.client.get(
            "/api/learning/metrics?recent_limit=5&recent_window_hours=48&baseline_window_hours=168&alert_min_samples=1"
        )
        self.assertEqual(metrics_response.status_code, 200)

        payload = metrics_response.json()
        self.assertIn("status", payload)
        self.assertIn("recent_feedback", payload)
        self.assertIn("quality_threshold", payload)
        self.assertIn("windows", payload)
        self.assertIn("alerts", payload)

        status = payload["status"]
        self.assertIn("summary", status)
        summary = status["summary"]
        self.assertIn("global_brier_score", summary)
        self.assertIn("global_calibration_gap", summary)
        self.assertIn("global_roi_count", summary)

        threshold = payload["quality_threshold"]
        self.assertIn("effective_min_probability", threshold)
        self.assertIn("base_min_probability", threshold)

        windows = payload["windows"]
        self.assertIn("recent", windows)
        self.assertIn("baseline", windows)
        self.assertIn("trend_delta", windows)
        self.assertGreaterEqual(windows["recent"].get("samples", 0), 1)

        self.assertGreaterEqual(len(payload["alerts"]), 1)

        self.assertGreaterEqual(len(payload["recent_feedback"]), 1)
        first = payload["recent_feedback"][0]
        self.assertIn("sport", first)
        self.assertIn("predicted_probability", first)
        self.assertIn("brier_score", first)


if __name__ == "__main__":
    unittest.main()
