from __future__ import annotations

from typing import Any, Dict


class BaseAgent:
    agent_id: str = "base"
    name: str = "Base Agent"

    def run(self, event: Dict[str, Any], *, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        raise NotImplementedError

    def status(self) -> Dict[str, Any]:
        return {"agent_id": self.agent_id, "name": self.name, "status": "ready"}
