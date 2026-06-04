from __future__ import annotations

from typing import Any, Dict

from prediction.ml_model import predict_1x2_ml


def run(event: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, float]:
    return predict_1x2_ml(event, context)
