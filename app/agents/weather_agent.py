from __future__ import annotations

from typing import Any, Dict

from agents.base import BaseAgent
from prediction.weather import weather_context


class WeatherAgent(BaseAgent):
    agent_id = "weather"
    name = "Weather Agent"

    def run(self, event: Dict[str, Any], *, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        return weather_context(event)
