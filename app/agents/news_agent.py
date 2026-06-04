from __future__ import annotations

from typing import Any, Dict

from agents.base import BaseAgent


class NewsAgent(BaseAgent):
    agent_id = "news"
    name = "News Agent"

    def run(self, event: Dict[str, Any], *, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        sentiment = event.get("news_sentiment") or {}
        return {
            "sources": ["twitter", "telegram", "club_sites", "insiders"],
            "sentiment_index": float(sentiment.get("index") or 0.0),
            "home_bias": float(sentiment.get("home_bias") or 0.0),
            "away_bias": float(sentiment.get("away_bias") or 0.0),
            "headlines": event.get("news_headlines") or [],
        }
