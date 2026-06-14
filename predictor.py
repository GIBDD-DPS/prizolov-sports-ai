import logging
import pickle
from pathlib import Path
from fetcher import fetch_live_data

logger = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).parent / "model.pkl"

def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Модель не найдена: {MODEL_PATH}")
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)

def get_prediction():
    try:
        data = fetch_live_data()
        if "error" in data:
            return {"error": data["error"]}

        model = load_model()
        features = preprocess(data)  # ваша подготовка признаков
        winner = model.predict(features)[0]
        proba = model.predict_proba(features)[0]
        probability = round(max(proba) * 100, 1)

        return {
            "winner": str(winner),
            "probability": probability
        }
    except FileNotFoundError:
        logger.error("Файл модели не найден")
        return {"error": "model_not_found"}
    except Exception as e:
        logger.exception("Ошибка прогнозирования")
        return {"error": "prediction_failed"}

def preprocess(data):
    """
    Преобразует сырые данные из API в признаки для модели.
    ЗАМЕНИТЕ НА РЕАЛЬНУЮ ЛОГИКУ.
    Пример: возвращайте список списков или DataFrame.
    """
    # Заглушка, чтобы модель не падала
    return [[0.0]]
