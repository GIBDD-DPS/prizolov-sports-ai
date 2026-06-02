#!/usr/bin/env python3
# ============================================
# Prizolov Sports AI - Self-Learning Auto Feedback Worker
# Version: 12.1
# ============================================

import argparse
import datetime
import hashlib
import json
import logging
import pathlib
import random
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PrizolovSportsAI.AutoFeedbackWorker")

DEFAULT_STATE_PATH = "runtime/auto_feedback_worker_state.json"
DEFAULT_API_BASE_URL = "http://127.0.0.1:8080"

SCORE_RE = re.compile(r"^\s*(\d+)\s*[-:]\s*(\d+)\s*$")
DRAW_TOKENS = {"draw", "x", "ничья", "drawn"}


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _utcnow_iso() -> str:
    return _utcnow().isoformat()


def _parse_iso(value: Optional[str]) -> Optional[datetime.datetime]:
    if not value:
        return None
    try:
        return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_probability(value: Any) -> float:
    probability = _safe_float(value, 0.5)
    return max(0.01, min(0.99, probability))


def _build_state() -> Dict[str, Any]:
    return {
        "updated_at": None,
        "pending": {},
        "sent": {},
        "stats": {
            "total_pending_created": 0,
            "total_feedback_sent": 0,
        },
    }


def _load_state(path: pathlib.Path) -> Dict[str, Any]:
    if not path.exists():
        return _build_state()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Не удалось прочитать state %s: %s", path, exc)
        return _build_state()

    if not isinstance(payload, dict):
        return _build_state()

    state = _build_state()
    if isinstance(payload.get("pending"), dict):
        state["pending"] = payload["pending"]
    if isinstance(payload.get("sent"), dict):
        state["sent"] = payload["sent"]
    if isinstance(payload.get("stats"), dict):
        state["stats"] = payload["stats"]
    state["updated_at"] = payload.get("updated_at")
    return state


def _save_state(path: pathlib.Path, state: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _utcnow_iso()
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _http_json(
    url: str,
    method: str = "GET",
    payload: Optional[Dict[str, Any]] = None,
    timeout: float = 15.0,
) -> Dict[str, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url=url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        if not body.strip():
            return {}
        decoded = json.loads(body)
        if isinstance(decoded, dict):
            return decoded
        return {"data": decoded}


def _fetch_events(api_base_url: str, lang: str, timeout: float) -> Dict[str, Any]:
    query = urllib.parse.urlencode({"lang": lang})
    url = f"{api_base_url.rstrip('/')}/api/all-events?{query}"
    return _http_json(url, method="GET", timeout=timeout)


def _post_feedback(
    api_base_url: str,
    sport: str,
    predicted_probability: float,
    outcome: bool,
    timeout: float,
    metadata: Optional[Dict[str, Any]] = None,
    coefficient: Optional[float] = None,
    closing_coefficient: Optional[float] = None,
) -> Dict[str, Any]:
    url = f"{api_base_url.rstrip('/')}/api/learning/feedback"
    payload = {
        "sport": sport,
        "predicted_probability": predicted_probability,
        "outcome": outcome,
    }
    if coefficient is not None and coefficient > 1.0:
        payload["coefficient"] = coefficient
    if closing_coefficient is not None and closing_coefficient > 1.0:
        payload["closing_coefficient"] = closing_coefficient
    if isinstance(metadata, dict):
        if metadata.get("event_id"):
            payload["event_id"] = metadata.get("event_id")
        if metadata.get("line"):
            payload["line"] = metadata.get("line")
        if metadata.get("source"):
            payload["source"] = metadata.get("source")
    return _http_json(url, method="POST", payload=payload, timeout=timeout)


def _is_learning_api_available(api_base_url: str, timeout: float) -> bool:
    url = f"{api_base_url.rstrip('/')}/api/learning/status"
    try:
        _http_json(url, method="GET", timeout=timeout)
        return True
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            logger.warning(
                "Learning API endpoint not found on target (%s). "
                "Deploy backend with /api/learning/* before production feedback mode.",
                api_base_url,
            )
            return False
        logger.warning("Learning API preflight HTTP error: %s", exc)
        return False
    except urllib.error.URLError as exc:
        logger.warning("Learning API preflight network error: %s", exc)
        return False
    except Exception as exc:
        logger.warning("Learning API preflight failed: %s", exc)
        return False


def _normalize_sport(sport: Any) -> str:
    raw = str(sport or "other").strip().lower()
    if not raw:
        return "other"
    return raw


def _make_prediction_key(event_id: str, line: str, sport: str) -> str:
    raw = f"{event_id}::{line}::{sport}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _extract_h2h_outcome(
    line: str,
    home: str,
    away: str,
    score: str,
) -> Optional[bool]:
    line_lower = (line or "").strip().lower()
    if not line_lower.startswith("h2h:"):
        return None

    score_match = SCORE_RE.match(str(score or "").strip())
    if not score_match:
        return None

    home_score = int(score_match.group(1))
    away_score = int(score_match.group(2))
    target = line.split(":", 1)[1].strip().lower()

    home_norm = str(home or "").strip().lower()
    away_norm = str(away or "").strip().lower()

    if target == home_norm:
        return home_score > away_score
    if target == away_norm:
        return away_score > home_score
    if target in DRAW_TOKENS:
        return home_score == away_score
    return None


def _bootstrap_outcome(key: str, probability: float) -> bool:
    seed = int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:8], 16)
    rng = random.Random(seed)
    return rng.random() < probability


def _collect_pending_predictions(
    state: Dict[str, Any],
    events_payload: Dict[str, Any],
    max_recommendations_per_event: int,
) -> int:
    events = events_payload.get("events")
    if not isinstance(events, list):
        return 0

    created = 0
    now_iso = _utcnow_iso()
    pending = state.setdefault("pending", {})
    sent = state.setdefault("sent", {})
    stats = state.setdefault("stats", {})

    for event in events:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("id") or event.get("home") or "unknown_event")
        sport = _normalize_sport(event.get("sport_code") or event.get("sport"))
        recommendations = event.get("recommendations")
        if not isinstance(recommendations, list):
            continue

        for rec in recommendations[:max(1, max_recommendations_per_event)]:
            if not isinstance(rec, dict):
                continue
            line = str(rec.get("line") or "").strip()
            if not line:
                continue
            probability = _normalize_probability(rec.get("base_probability", rec.get("probability", 0.5)))
            key = _make_prediction_key(event_id, line, sport)

            if key in pending or key in sent:
                continue

            pending[key] = {
                "event_id": event_id,
                "sport": sport,
                "line": line,
                "home": event.get("home"),
                "away": event.get("away"),
                "score": event.get("score"),
                "coefficient": rec.get("coefficient"),
                "opening_coefficient": rec.get("coefficient"),
                "latest_coefficient": rec.get("coefficient"),
                "predicted_probability": probability,
                "first_seen_at": now_iso,
                "last_seen_at": now_iso,
            }
            created += 1

    stats["total_pending_created"] = _safe_int(stats.get("total_pending_created"), 0) + created
    return created




def _extract_recommendation_coefficient(event: Dict[str, Any], line: str) -> Optional[float]:
    recommendations = event.get("recommendations")
    if not isinstance(recommendations, list):
        return None

    target = str(line or "").strip()
    if not target:
        return None

    for rec in recommendations:
        if not isinstance(rec, dict):
            continue
        if str(rec.get("line") or "").strip() != target:
            continue
        coefficient = _safe_float(rec.get("coefficient"), 0.0)
        if coefficient > 1.0:
            return coefficient
    return None


def _refresh_pending_scores(state: Dict[str, Any], events_payload: Dict[str, Any]) -> None:
    events = events_payload.get("events")
    if not isinstance(events, list):
        return

    events_by_id: Dict[str, Dict[str, Any]] = {}
    for event in events:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("id") or event.get("home") or "unknown_event")
        events_by_id[event_id] = event

    now_iso = _utcnow_iso()
    for item in state.get("pending", {}).values():
        if not isinstance(item, dict):
            continue
        event_id = str(item.get("event_id") or "")
        current_event = events_by_id.get(event_id)
        if current_event:
            item["score"] = current_event.get("score")
            latest_coefficient = _extract_recommendation_coefficient(current_event, str(item.get("line") or ""))
            if latest_coefficient is not None:
                item["latest_coefficient"] = latest_coefficient
            item["last_seen_at"] = now_iso


def _resolve_outcome(
    key: str,
    prediction: Dict[str, Any],
    bootstrap_when_unresolved: bool,
) -> Tuple[Optional[bool], str]:
    outcome = _extract_h2h_outcome(
        line=str(prediction.get("line") or ""),
        home=str(prediction.get("home") or ""),
        away=str(prediction.get("away") or ""),
        score=str(prediction.get("score") or ""),
    )
    if outcome is not None:
        return outcome, "score_h2h"

    if bootstrap_when_unresolved:
        probability = _normalize_probability(prediction.get("predicted_probability", 0.5))
        return _bootstrap_outcome(key, probability), "bootstrap_probability"

    return None, "unresolved"


def _process_pending_feedback(
    state: Dict[str, Any],
    api_base_url: str,
    settle_seconds: int,
    timeout: float,
    max_feedback_per_run: int,
    bootstrap_when_unresolved: bool,
    expire_pending_seconds: int,
    dry_run: bool,
    feedback_api_enabled: bool,
) -> Dict[str, int]:
    now = _utcnow()
    stats = state.setdefault("stats", {})
    pending = state.setdefault("pending", {})
    sent = state.setdefault("sent", {})

    sent_now = 0
    skipped_unresolved = 0
    expired = 0
    blocked_api = 0

    to_delete = []
    pending_items = sorted(
        ((key, value) for key, value in pending.items() if isinstance(value, dict)),
        key=lambda pair: str(pair[1].get("first_seen_at") or ""),
    )

    for key, prediction in pending_items:
        if sent_now >= max_feedback_per_run:
            break

        first_seen = _parse_iso(str(prediction.get("first_seen_at") or ""))
        if first_seen is None:
            first_seen = now
        age_seconds = (now - first_seen).total_seconds()

        if age_seconds < settle_seconds:
            continue

        outcome, outcome_source = _resolve_outcome(
            key=key,
            prediction=prediction,
            bootstrap_when_unresolved=bootstrap_when_unresolved,
        )

        if outcome is None:
            if age_seconds >= expire_pending_seconds:
                sent[key] = {
                    "status": "expired_unresolved",
                    "expired_at": _utcnow_iso(),
                    "sport": prediction.get("sport"),
                    "line": prediction.get("line"),
                }
                to_delete.append(key)
                expired += 1
            else:
                skipped_unresolved += 1
            continue

        sport = _normalize_sport(prediction.get("sport"))
        probability = _normalize_probability(prediction.get("predicted_probability", 0.5))

        if dry_run:
            logger.info(
                "[dry-run] feedback sport=%s probability=%.4f outcome=%s source=%s",
                sport,
                probability,
                outcome,
                outcome_source,
            )
            sent_now += 1
            continue

        if not feedback_api_enabled:
            blocked_api += 1
            continue

        payload_metadata = {
            "event_id": prediction.get("event_id"),
            "line": prediction.get("line"),
            "source": "auto_feedback_worker",
        }

        opening_coefficient = prediction.get("opening_coefficient", prediction.get("coefficient"))
        latest_coefficient = prediction.get("latest_coefficient")
        extra_payload: Dict[str, Any] = {}
        opening_value = _safe_float(opening_coefficient, 0.0)
        closing_value = _safe_float(latest_coefficient, 0.0)
        if opening_value > 1.0:
            extra_payload["coefficient"] = opening_value
        if closing_value > 1.0:
            extra_payload["closing_coefficient"] = closing_value

        try:
            response = _post_feedback(
                api_base_url=api_base_url,
                sport=sport,
                predicted_probability=probability,
                outcome=outcome,
                timeout=timeout,
                metadata=payload_metadata,
                **extra_payload,
            )
        except urllib.error.HTTPError as exc:
            logger.warning("HTTP ошибка при отправке feedback: %s", exc)
            continue
        except urllib.error.URLError as exc:
            logger.warning("Сетевая ошибка при отправке feedback: %s", exc)
            continue
        except Exception as exc:
            logger.warning("Не удалось отправить feedback: %s", exc)
            continue

        sent_entry = {
            "status": "sent",
            "sent_at": _utcnow_iso(),
            "sport": sport,
            "line": prediction.get("line"),
            "predicted_probability": probability,
            "outcome": bool(outcome),
            "outcome_source": outcome_source,
            "opening_coefficient": opening_value if opening_value > 1.0 else None,
            "closing_coefficient": closing_value if closing_value > 1.0 else None,
            "api_response_ok": bool(response.get("ok", False)),
        }
        if opening_value > 1.0 and closing_value > 1.0:
            sent_entry["clv_delta"] = round(opening_value - closing_value, 5)
        sent[key] = sent_entry
        to_delete.append(key)
        sent_now += 1

    for key in to_delete:
        pending.pop(key, None)

    stats["total_feedback_sent"] = _safe_int(stats.get("total_feedback_sent"), 0) + sent_now

    return {
        "sent_now": sent_now,
        "skipped_unresolved": skipped_unresolved,
        "expired": expired,
        "blocked_api": blocked_api,
    }


def _prune_sent(state: Dict[str, Any], retention_days: int) -> int:
    sent = state.setdefault("sent", {})
    now = _utcnow()
    max_age_seconds = max(1, retention_days) * 86400
    removed = 0

    for key in list(sent.keys()):
        item = sent.get(key)
        if not isinstance(item, dict):
            sent.pop(key, None)
            removed += 1
            continue

        ts = _parse_iso(str(item.get("sent_at") or item.get("expired_at") or ""))
        if ts is None:
            continue
        if (now - ts).total_seconds() > max_age_seconds:
            sent.pop(key, None)
            removed += 1

    return removed


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Auto feedback worker for self-learning sports API",
    )
    parser.add_argument(
        "--api-base-url",
        default=DEFAULT_API_BASE_URL,
        help="Base URL of FastAPI service, e.g. http://127.0.0.1:8080",
    )
    parser.add_argument("--lang", default="en", help="Language for event fetch (ru/en)")
    parser.add_argument("--state-path", default=DEFAULT_STATE_PATH, help="Path to worker state JSON")
    parser.add_argument("--settle-seconds", type=int, default=7200, help="Age before pending prediction can be settled")
    parser.add_argument("--expire-pending-seconds", type=int, default=172800, help="Drop unresolved pending predictions after this age")
    parser.add_argument("--max-recommendations-per-event", type=int, default=1, help="How many recommendations per event to track")
    parser.add_argument("--max-feedback-per-run", type=int, default=25, help="Maximum feedback posts per single run")
    parser.add_argument("--retention-days", type=int, default=14, help="Keep sent feedback records for N days")
    parser.add_argument("--request-timeout", type=float, default=15.0, help="HTTP timeout in seconds")
    parser.add_argument(
        "--bootstrap-when-unresolved",
        action="store_true",
        help="If score-based settlement is impossible, generate probabilistic bootstrap outcome",
    )
    parser.add_argument("--dry-run", action="store_true", help="Do not POST feedback, only log actions")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    state_path = pathlib.Path(args.state_path)
    state = _load_state(state_path)

    logger.info("Загрузка событий из %s", args.api_base_url)
    try:
        events_payload = _fetch_events(
            api_base_url=args.api_base_url,
            lang=args.lang,
            timeout=args.request_timeout,
        )
    except Exception as exc:
        logger.error("Не удалось загрузить события: %s", exc)
        return 1

    created = _collect_pending_predictions(
        state=state,
        events_payload=events_payload,
        max_recommendations_per_event=args.max_recommendations_per_event,
    )
    _refresh_pending_scores(state, events_payload)

    feedback_api_enabled = True
    if not args.dry_run:
        feedback_api_enabled = _is_learning_api_available(
            api_base_url=args.api_base_url,
            timeout=args.request_timeout,
        )

    processing = _process_pending_feedback(
        state=state,
        api_base_url=args.api_base_url,
        settle_seconds=max(0, args.settle_seconds),
        timeout=args.request_timeout,
        max_feedback_per_run=max(1, args.max_feedback_per_run),
        bootstrap_when_unresolved=args.bootstrap_when_unresolved,
        expire_pending_seconds=max(1, args.expire_pending_seconds),
        dry_run=args.dry_run,
        feedback_api_enabled=feedback_api_enabled,
    )
    pruned = _prune_sent(state, retention_days=max(1, args.retention_days))

    _save_state(state_path, state)

    logger.info(
        "Готово: new_pending=%d sent_now=%d unresolved=%d expired=%d blocked_api=%d pending_total=%d sent_total=%d pruned=%d",
        created,
        processing["sent_now"],
        processing["skipped_unresolved"],
        processing["expired"],
        processing["blocked_api"],
        len(state.get("pending", {})),
        len(state.get("sent", {})),
        pruned,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
