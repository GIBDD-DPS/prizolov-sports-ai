# ============================================
# Prizolov Sports AI - Generative Preview & Media Poster Engine
# Version: 5.03 (Generative AI Poster Core)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Automated SEO Content & Generative AI Graphic Banners
# ============================================

import sys
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

import cv2
import numpy as np
import httpx # Асинхронный HTTP-клиент для работы с внешним Генеративным ИИ

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

logger = logging.getLogger("PrizolovSportsAI.GenerativePreview")

class GenerativePreviewEngine:
    """Мультимодальный ИИ-модуль для автоматического создания экспертных текстовых обзоров и ИИ-генерации баннеров"""

    def __init__(self, base_data_dir: str = "/data"):
        self.data_dir = Path(base_data_dir)
        self.logo_path = self.data_dir / "branding" / "prizolov_logo.png"
        self.players_dir = self.data_dir / "players"
        
        # Инжекция API-ключа генеративной нейросети из переменных среды Amvera
        # Поддерживает DALL-E / Stability AI / Любой внутренний инференс-сервер Prizolov Lab
        self.gen_ai_api_key = os.getenv("PRIZOLOV_GENERATIVE_IMAGE_API_KEY", "")
        self.gen_ai_endpoint = "https://prizolov.ru"

    def generate_match_preview_text(self, match_id: str, team_a: str, team_b: str, sport: str, lambda_a: float, lambda_b: float, capper_sentiment_trend: str = "over") -> str:
        """Генерирует развернутый аналитический текстовый разбор матча"""
        logger.info(f"[Generative AI] Сборка текстового превью для матча {match_id} ({team_a} vs {team_b})...")
        
        if abs(lambda_a - lambda_b) < 0.25:
            strength_analysis = f"Обе команды подходят к live-встрече в сопоставимой форме. Математическая модель ИИ Prizolov Lab фиксирует паритет сил."
            prediction_tip = "Наиболее безопасным выбором здесь выглядит ставка на обоюдную результативность (Обе забьют - Да) или плюсовые форы аутсайдера."
        elif lambda_a > lambda_b:
            strength_analysis = f"Аналитическое ядро Prizolov AI выделяет {team_a} в качестве явного фаворита данного противостояния. Интенсивность их атакующих действий значительно превосходит оборонительный потенциал оппонента."
            prediction_tip = f"Рекомендуется присмотреться к чистой победе {team_a} или аккуратной минусовой форе (-1)."
        else:
            strength_analysis = f"Команда {team_b} имеет выраженное преимущество по ключевым метрикам предматчевого контекста. Вероятность их доминирования на чужой половине поля оценивается экспертной системой как повышенная."
            prediction_tip = f"Логичным решением для купона будет фора (0) на {team_b} или их individual тотал больше."

        if capper_sentiment_trend == "over":
            sentiment_paragraph = "Экспертное сообщество верификаторов и капперов платформы prizolov.ru единогласно ожидает открытый, атакующий футбол с обилием опасных моментов. Тренды сентимент-анализа указывают на перегруз верховых маркетов."
        else:
            sentiment_paragraph = "Большинство профессиональных live-аналитиков склоняются к прагматичному, закрытому сценарию матча. Защитные редуты обеих сторон будут превалировать над созиданием."

        preview_article = [
            f"=== АНАЛИТИЧЕСКИЙ ПРЕВЬЮ-ОБЗОР МАТЧА: {team_a.upper()} ПРОТИВ {team_b.upper()} ===",
            f"В рамках текущего live-сезона по виду спорта {sport} нас ожидает интригующее противостояние.",
            strength_analysis,
            sentiment_paragraph,
            "--- ИИ-ПРОГНОЗ ОТ ЛАБОРАТОРИИ PRIZOLOV SPORTS ---",
            prediction_tip,
            "================================================"
        ]
        return "\n\n".join(preview_article)

    async def _download_ai_generated_player(self, player_prompt: str) -> Optional[np.ndarray]:
        """Асинхронно запрашивает генерацию изображения игрока у внешней ИИ-нейросети"""
        if not self.gen_ai_api_key:
            return None
            
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"Authorization": f"Bearer {self.gen_ai_api_key}", "Content-Type": "application/json"}
                payload = {"prompt": player_prompt, "steps": 20, "width": 510, "height": 700}
                
                response = await client.post(self.gen_ai_endpoint, json=payload, headers=headers)
                if response.status_code == 200:
                    # Декодируем бинарную картинку напрямую в матрицу OpenCV
                    image_bytes = np.frombuffer(response.content, dtype=np.uint8)
                    img = cv2.imdecode(image_bytes, cv2.IMREAD_UNCHANGED)
                    return img
        except Exception as e:
            logger.error(f"[Generative AI Network Error] Не удалось сгенерировать лицо игрока: {e}")
        return None

    async def generate_match_promo_banner(self, 
                                          match_id: str, 
                                          team_a: str, 
                                          team_b: str, 
                                          sport: str,
                                          player_a_desc: str, 
                                          player_b_desc: str) -> Optional[str]:
        """
        Ультимативный метод: Динамически генерирует через ИИ или подгружает фото игроков,
        верстает HD-промо-баннер матча и сохраняет на диск Amvera Cloud.
        """
        try:
            # 1. Инициализация подложки баннера (1920x1080)
            banner = np.zeros((1080, 1920, 3), dtype=np.uint8)
            for y in range(1080):
                color_val = int(24 + (y / 1080) * 15)
                banner[y, :] = (color_val, color_val, 28)

            cv2.line(banner, (960, 200), (960, 900), (97, 211, 4), 2) # Зеленый бренд-лайнер Prizolov

            # 2. ИИ-Генерация или фолбэк-загрузка Игрока А (Слева)
            img_p_a = None
            if self.gen_ai_api_key:
                prompt_a = f"A professional {sport} player, face, athletic body, {player_a_desc}, photorealistic, sports card style"
                img_p_a = await self._download_ai_generated_player(prompt_a)
                
            if img_p_a is None: # Фолбэк на локальный файл, если ИИ-сеть отключена
                local_path_a = self.players_dir / f"{team_a.lower()}_star.png"
                if local_path_a.exists():
                    img_p_a = cv2.imread(str(local_path_a), cv2.IMREAD_UNCHANGED)

            if img_p_a is not None:
                p_a_res = cv2.resize(img_p_a, (500, 700))
                banner[200:900, 200:700] = np.where(p_a_res > 10, p_a_res, banner[200:900, 200:700])

            # 3. ИИ-Генерация или фолбэк-загрузка Игрока Б (Справа)
            img_p_b = None
            if self.gen_ai_api_key:
                prompt_b = f"A professional {sport} player, face, athletic body, {player_b_desc}, photorealistic, sports card style"
                img_p_b = await self._download_ai_generated_player(prompt_b)
                
            if img_p_b is None:
                local_path_b = self.players_dir / f"{team_b.lower()}_star.png"
                if local_path_b.exists():
                    img_p_b = cv2.imread(str(local_path_b), cv2.IMREAD_UNCHANGED)

            if img_p_b is not None:
                p_b_res = cv2.resize(img_p_b, (500, 700))
                banner[200:900, 1220:1720] = np.where(p_b_res > 10, p_b_res, banner[200:900, 1220:1720])

            # 4. Печать текстовых блоков и Versus разметки
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(banner, team_a.upper(), (200, 960), font, 1.8, (255, 255, 255), 3, cv2.LINE_AA)
            cv2.putText(banner, "VS", (920, 560), font, 2.2, (97, 211, 4), 4, cv2.LINE_AA)
            cv2.putText(banner, team_b.upper(), (1220, 960), font, 1.8, (255, 255, 255), 3, cv2.LINE_AA)

            # 5. Наложение вотермарка/логотипа Prizolov.ru
            if self.logo_path.exists():
                logo = cv2.imread(str(self.logo_path), cv2.IMREAD_UNCHANGED)
                if logo is not None:
                    logo_res = cv2.resize(logo, (360, 90))
                    banner[40:130, 800:1160] = np.where(logo_res > 10, logo_res, banner[40:130, 800:1160])
            else:
                cv2.putText(banner, "PRIZOLOV.RU", (800, 100), font, 1.5, (97, 211, 4), 3, cv2.LINE_AA)

            # Экспорт баннера в персистентную директорию
            output_banner_path = self.data_dir / f"banners/promo_{match_id}.jpg"
            output_banner_path.parent.mkdir(parents=True, exist_ok=True)
            
            cv2.imwrite(str(output_banner_path), banner, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
            logger.info(f"[Generative AI Banner] Промо-постер сохранен по пути: {output_banner_path}")
            return str(output_banner_path)

        except Exception as e:
            logger.error(f"Критический сбой генеративного медиа-модуля: {e}")
            return None
