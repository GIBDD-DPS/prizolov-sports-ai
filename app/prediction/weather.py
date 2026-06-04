# Weather impact: football wind/rain/temp; tennis humidity/court speed.

from __future__ import annotations

from typing import Any, Dict


def weather_context(event: Dict[str, Any], wx: Dict[str, Any] | None = None) -> Dict[str, Any]:
    sport = str(event.get("sport") or "football").lower()
    data = wx or event.get("weather") or {}
    if sport == "tennis":
        humidity = float(data.get("humidity") or 55)
        surface = str(data.get("surface") or "hard")
        court_speed = str(data.get("court_speed") or "medium")
        serve_bias = 0.02 if humidity > 70 else 0.0
        return {
            "sport": sport,
            "humidity": humidity,
            "surface": surface,
            "court_speed": court_speed,
            "goal_bias_home": serve_bias,
            "goal_bias_away": -serve_bias * 0.5,
        }
    wind = float(data.get("wind_kmh") or 8)
    rain = bool(data.get("rain") or data.get("precipitation_mm", 0) > 1)
    temp = float(data.get("temp_c") or 12)
    under_bias = 0.03 if rain or wind > 25 else 0.0
    if temp < 2:
        under_bias += 0.02
    return {
        "sport": sport,
        "wind_kmh": wind,
        "rain": rain,
        "temp_c": temp,
        "total_goals_bias": -under_bias,
        "notes": "Дождь/ветер снижают темп и xG" if under_bias else None,
    }
