# Prediction Engine (Ensemble 1X2)

Probabilistic match outcome module used before LLM explanation in the storefront pipeline.

## Output format

```json
{
  "home_win": 0.51,
  "draw": 0.24,
  "away_win": 0.25
}
```

Each storefront event may also include `prediction.explanation`, `prediction.quality`, and `prediction.modules`.

## Ensemble weights

| Agent | Weight | Role |
|-------|--------|------|
| Model | 40% | LightGBM / heuristic 1X2 |
| Market | 25% | Implied probabilities from odds |
| xG | 15% | Football xG/xGA profile |
| Form | 10% | Elo + calendar strength |
| News | 10% | Sentiment tilt (placeholder) |

## Modules

- **xG (football)**: xG, xGA, big chances, shots on target, PPDA, possession
- **Lineups**: confirmed lineups, injuries, suspensions, rotation risk
- **Calendar**: opponent strength, rest days, travel, fixture congestion
- **Line movement**: opening vs current coefficient, hourly delta
- **CLV**: coefficient at prediction vs pre-kickoff
- **Referee**: cards, fouls, penalty rate
- **Weather**: wind/rain/temp (football), humidity/court (tennis)
- **Motivation**: title race, relegation, dead rubber
- **Learning**: post-match ledger for ROI by market/league

## API

- `GET /api/predict/outcome?home=...&away=...&sport=football`
- `POST /api/predict/outcome` — body: event object or `{ "event": {...} }`
- `GET /api/predict/summary` — events with 1X2 for dashboard
- `GET /api/predict/learning` — insights from learning ledger
- `POST /api/predict/learning/result` — record match result for auto-learning

Storefront events from `/api/all-events` include `prediction` when the ensemble pipeline runs.

## Environment

- `PREDICTION_STATE_PATH` — Elo, CLV, line opening, learning ledger (default: `runtime/prediction_state.json`)
- `PREDICTION_MODEL_PATH` — joblib LightGBM model (default: `runtime/prediction_lgbm.joblib`)
- `EXPLAIN_LLM_ENABLED` — future hook for external LLM explanation

## Bootstrap ML model

```bash
cd app && PYTHONPATH=. python -c "from prediction.ml_model import train_bootstrap_model; train_bootstrap_model()"
```
