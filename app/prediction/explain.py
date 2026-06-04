# LLM-style explanation (template; plug OpenAI via EXPLAIN_LLM_ENABLED).

from __future__ import annotations

import os
from typing import Any, Dict


def explain_prediction(
    event: Dict[str, Any],
    probabilities: Dict[str, float],
    context: Dict[str, Any],
    quality: Dict[str, Any],
) -> str:
    if os.getenv("EXPLAIN_LLM_ENABLED", "").lower() in {"1", "true", "yes"}:
        # Hook for future OpenAI/Anthropic call
        pass

    home = event.get("home") or "Хозяева"
    away = event.get("away") or "Гости"
    h = int(round(float(probabilities.get("home_win") or 0) * 100))
    d = int(round(float(probabilities.get("draw") or 0) * 100))
    a = int(round(float(probabilities.get("away_win") or 0) * 100))
    xg = context.get("xg_profile") or {}
    lineup = context.get("lineup") or {}
    cal = context.get("calendar") or {}
    mot = context.get("motivation") or {}
    ref = context.get("referee") or {}
    wx = context.get("weather") or {}

    parts = [
        f"Ансамбль моделей оценивает матч {home} — {away}: П1 {h}%, X {d}%, П2 {a}%.",
        f"Уверенность {quality.get('confidence_label', '—')}, value {quality.get('value_label', '—')}, риск {quality.get('risk', '—')}.",
    ]
    if xg.get("football_extended"):
        parts.append(
            f"xG {xg.get('xg_home', '—')}:{xg.get('xg_away', '—')}, "
            f"SOT {xg.get('shots_on_target_home', '—')}-{xg.get('shots_on_target_away', '—')}, "
            f"владение {xg.get('possession_home', '—')}%."
        )
    if lineup.get("risk_flags"):
        parts.append(f"Составы: {', '.join(lineup['risk_flags'])} — снизили уверенность.")
    if cal.get("rest_days_home") is not None:
        parts.append(f"Календарь: отдых {cal.get('rest_days_home')} vs {cal.get('rest_days_away')} дн.")
    if mot.get("home_tags") or mot.get("away_tags"):
        parts.append("Мотивация учтена в Form/News агентах.")
    if ref.get("avg_yellow_cards"):
        parts.append(f"Судья: ~{ref['avg_yellow_cards']} ЖК за матч ({ref.get('style', '—')}).")
    if wx.get("rain") or (wx.get("wind_kmh", 0) or 0) > 20:
        parts.append("Погода может снизить темп (дождь/ветер).")
    lm = context.get("line_movement") or {}
    if lm.get("moves"):
        parts.append(f"Движение линии: {len(lm['moves'])} заметных сдвигов с открытия.")
    return " ".join(parts)
