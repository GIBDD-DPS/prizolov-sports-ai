import os

# API-ключ только из переменной окружения
SPORTS_API_KEY = os.getenv("SPORTS_API_KEY")
if not SPORTS_API_KEY:
    raise RuntimeError("Переменная окружения SPORTS_API_KEY не задана!")

# URL вашего источника данных (замените на реальный)
SPORTS_API_URL = os.getenv("SPORTS_API_URL", "https://api.sportsdata.io/v3/...")

CACHE_TTL = 300  # секунд
