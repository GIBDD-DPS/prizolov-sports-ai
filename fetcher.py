import logging
import requests
from config import SPORTS_API_URL, SPORTS_API_KEY

logger = logging.getLogger(__name__)

def fetch_live_data():
    """
    Запрашивает данные из спортивного API.
    Возвращает словарь данных или {'error': 'описание'}.
    """
    headers = {"Authorization": f"Bearer {SPORTS_API_KEY}"}
    try:
        resp = requests.get(SPORTS_API_URL, headers=headers, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.Timeout:
        logger.error("Таймаут при запросе к API")
        return {"error": "timeout"}
    except requests.exceptions.HTTPError as e:
        logger.error("HTTP ошибка: %s", e)
        return {"error": f"http_{resp.status_code}"}
    except requests.exceptions.RequestException as e:
        logger.error("Сетевая ошибка: %s", e)
        return {"error": "network_error"}
    except ValueError:
        logger.error("Некорректный JSON в ответе")
        return {"error": "invalid_json"}
