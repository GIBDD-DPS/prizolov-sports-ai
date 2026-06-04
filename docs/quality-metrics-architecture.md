# Quality Metrics & Professional Architecture

## Layers

```
DATA (agents/) → FEATURE ENGINE (core/features/) → ML (models/) → VALUE → LLM → RESULT TRACKER → API → Site
```

## Modules

| Path | Role |
|------|------|
| `app/core/metrics/` | Accuracy, ROI, Yield, CLV periods, Brier, bet display scores |
| `app/core/system_monitor/` | Latency stages, error rate, uptime, data freshness |
| `app/core/features/` | Elo, xG, Form, Fatigue, Team Strength ratings |
| `app/agents/` | 10 specialized agents (odds, injury, form, xG, market, referee, weather, news, value, results) |
| `app/models/` | LightGBM + XGBoost + CatBoost ensemble |
| `app/analytics/` | v15 CLV, ROI ledger, line movement (PARI/Pinnacle) |
| `app/prediction/` | Ensemble 1X2 + explanation |

## API

- `GET /health` — uptime, freshness, latency, errors
- `GET /api/metrics/quality` — full quality dashboard
- `GET /api/metrics/clv?period=day|week|month|all`
- `GET /api/system/latency`
- `GET /api/system/freshness`
- `GET /api/agents/status`
- `POST /api/agents/run` — run all agents on event
- `POST /api/metrics/result` — settle bet, update ROI/Brier/CLV
- `GET /api/features/build`
- `GET /api/models/ensemble`

## Bet display (each recommendation)

`bet_display`: confidence 0–100, value %, EV %, risk LOW/MEDIUM/HIGH, kelly_stake_percent.
