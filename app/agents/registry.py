from __future__ import annotations

from typing import Any, Dict, List, Type

from agents.form_agent import FormAgent
from agents.injury_agent import InjuryAgent
from agents.market_intelligence import MarketIntelligenceAgent
from agents.news_agent import NewsAgent
from agents.odds_scanner import OddsScannerAgent
from agents.referee_agent import RefereeAgent
from agents.result_tracker import ResultTrackerAgent
from agents.value_detector import ValueDetectorAgent
from agents.weather_agent import WeatherAgent
from agents.xg_agent import XGAgent
from agents.base import BaseAgent

_AGENTS: List[BaseAgent] = [
    OddsScannerAgent(),
    InjuryAgent(),
    FormAgent(),
    XGAgent(),
    MarketIntelligenceAgent(),
    RefereeAgent(),
    WeatherAgent(),
    NewsAgent(),
    ValueDetectorAgent(),
    ResultTrackerAgent(),
]


def list_agents() -> List[Dict[str, Any]]:
    return [a.status() for a in _AGENTS]


def run_all(event: Dict[str, Any], *, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return {a.agent_id: a.run(event, context=context) for a in _AGENTS}


def get_agent(agent_id: str) -> BaseAgent | None:
    for a in _AGENTS:
        if a.agent_id == agent_id:
            return a
    return None
