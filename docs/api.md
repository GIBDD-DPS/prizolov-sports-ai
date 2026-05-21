# API и WebSocket

## WebSocket Endpoint

**URL:** `wss://prizolov.ru/ws/sport`

### Основной Live-пакет

См. `docs/api_specification.json`

### Пример сообщения

```json
{
  "match_id": "match_12345",
  "sport": "football",
  "game_time": "67:42",
  "timestamp_ms": 1747850000000,
  "ball_state": { ... },
  "metrics": { ... },
  "line_data": { ... },
  "ai_recommendations": [
    {
      "market": "TO 2.5",
      "probability": 0.68,
      "odds": 1.92,
      "value": 0.12,
      "confidence": 0.74,
      "reasoning": "Высокий xG + momentum Team A"
    }
  ]
}
REST Endpoints (FastAPI)

GET /health — статус системы
GET /matches/live — список live-матчей
POST /analyze — разовый анализ матча
GET /models/status — статус загруженных моделей

Документация OpenAPI доступна по /docs при локальном запуске.
