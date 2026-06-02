from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_all_events_contains_value_metadata():
    response = client.get("/api/all-events")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] > 0
    first_event = payload["events"][0]
    assert first_event["recommendations_count"] >= 1
    first_recommendation = first_event["recommendations"][0]
    for key in ("edge", "bookmakers_support", "value_score", "is_premium", "selection_tier"):
        assert key in first_recommendation


def test_all_events_premium_only_filters_lines():
    response = client.get(
        "/api/all-events",
        params={
            "premium_only": "true",
            "min_edge": "0.15",
            "min_bookmakers_support": "5",
            "max_recommendations_per_event": "5",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["filters"]["premium_only"] is True
    assert payload["total"] > 0
    for event in payload["events"]:
        assert event["recommendations"]
        for recommendation in event["recommendations"]:
            assert recommendation["is_premium"] is True
            assert recommendation["edge"] >= 0.15
            assert recommendation["bookmakers_support"] >= 5


def test_state_endpoint_exposes_feature_flags_for_frontend():
    response = client.post("/api/state", params={"premium_only": "true"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["features"]["premium_lines_mode"] is True
    assert payload["filters"]["premium_only"] is True
    for recommendation in payload["recommendations"]:
        assert recommendation["is_premium"] is True


def test_top_recommendations_defaults_to_premium_mode():
    response = client.get("/api/recommendations/top")
    assert response.status_code == 200
    payload = response.json()
    assert payload["filters"]["premium_only"] is True
    assert payload["total"] > 0
    for recommendation in payload["recommendations"]:
        assert recommendation["is_premium"] is True
