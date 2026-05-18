# ============================================
# Prizolov Sports AI - Generative Preview & Media Poster Engine
# Version: 5.02 (Multimodal Media Engine)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Automated SEO Content & Graphic Banner Generation
# ============================================

import sys
import os
import logging
from pathlib import Path
from typing import Dict, Any

# Нативная высокопроизводительная графическая библиотека
import cv2
import numpy as np

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

logger = logging.getLogger("PrizolovSportsAI.GenerativePreview")

class GenerativePreviewEngine:
    """Мультимодальный ИИ-модуль для автоматического создания экспертных текстовых обзоров и графических баннеров на prizolov.ru"""

    def __init__(self, base_data_dir: str = "/data"):
        self.data_dir = Path(base_data_dir)
        # Пути к ассетам брендинга и лиц игроков
        self.logo_path = self.data_dir / "branding" / "prizolov_logo.png"
        self.players_dir = self.data_dir / "players"

    def generate_match_preview_text(self, 
                                    match_id: str, 
                                    team_a: str, 
                                    team_b: str, 
                                    sport: str, 
                                    lambda_a: float, 
                                    lambda_b: float,
                                    capper_sentiment_trend: str = "over") -> str:
        """Генерирует развернутый аналитический разбор матча на основе математических весов ИИ-ядра"""
        logger.info(f"[Generative AI] Сборка текстового превью для матча {match_id} ({team_a} vs {team_b})...")
        
        if abs(lambda_a - lambda_b) < 0.25:
            strength_analysis = f"Обе команды подходят к live-встрече в сопоставимой форме. Математическая модель ИИ Prizolov Lab фиксирует паритет сил."
            prediction_tip = "Наиболее безопасным выбором здесь выглядит ставка на обоюдную результативность (Обе забьют - Да) или плюсовые форы аутсайдера."
        elif lambda_a > lambda_b:
            strength_analysis = f"Аналитическое ядро Prizolov AI выделяет {team_a} в качестве явного фаворита данного противостояния. Интенсивность их атакующих действий значительно превосходит оборонительный потенциал оппонента."
            prediction_tip = f"Рекомендуется присмотреться к чистой победе {team_a} или аккуратной минусовой форе (-1)."
        else:
            strength_analysis = f"Команда {team_b} имеет выраженное преимущество по ключевым метрикам предматчевого контекста. Вероятность их доминирования на чужой половине поля оценивается экспертной системой как повышенная."
            prediction_tip = f"Логичным решением для купона будет фора (0) на {team_b} или их индивидуальный тотал больше."

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

    def generate_match_promo_banner(self, 
                                    match_id: str, 
                                    team_a: str, 
                                    team_b: str, 
                                    player_a_filename: str, 
                                    player_b_filename: str) -> Optional[str]:
        """
        Новое: Аппаратно собирает и рендерит графический JPEG-баннер матча.
        Накладывает логотип Prizolov.ru, фотографии ведущих игроков лицом к лицу (Versus) и названия команд.
        """
        try:
            # 1. Создаем высокотехнологичный темный фон (Full HD: 1920x1080 пикселей) в стиле prizolov.ru
            banner = np.zeros((1080, 1920, 3), dtype=np.uint8)
            # Заливаем градиентным темно-серым цветом
            for y in range(1080):
                color_val = int(24 + (y / 1080) * 15)
                banner[y, :] = (color_val, color_val, 28)

            # Рисуем разделяющую неоновую линию Versus по центру
            cv2.line(banner, (960, 200), (960, 900), (97, 211, 4), 2) # Зеленый цвет бренда Prizolov

            # 2. Накладываем изображение ведущего игрока Команды А (слева)
            img_player_a_path = self.players_dir / player_a_filename
            if img_player_a_path.exists():
                p_a = cv2.imread(str(img_player_a_path), cv2.IMREAD_UNCHANGED)
                if p_a is not None:
                    p_a_res = cv2.resize(p_a, (500, 700))
                    # Бесшовное альфа-наложение фото (вырезаем черный или прозрачный фон игрока)
                    banner[200:900, 200:700] = np.where(p_a_res > 10, p_a_res, banner[200:900, 200:700])

            # 3. Накладываем изображение ведущего игрока Команды Б (справа)
            img_player_b_path = self.players_dir / player_b_filename
            if img_player_b_path.exists():
                p_b = cv2.imread(str(img_player_b_path), cv2.IMREAD_UNCHANGED)
                if p_b is not None:
                    p_b_res = cv2.resize(p_b, (500, 700))
                    banner[200:900, 1220:1720] = np.where(p_b_res > 10, p_b_res, banner[200:900, 1220:1720])

            # 4. Рендеринг текста: Названия команд и маркер VS
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(banner, team_a.upper(), (200, 960), font, 1.8, (255, 255, 255), 3, cv2.LINE_AA)
            cv2.putText(banner, "VS", (920, 560), font, 2.2, (97, 211, 4), 4, cv2.LINE_AA)
            cv2.putText(banner, team_b.upper(), (1220, 960), font, 1.8, (255, 255, 255), 3, cv2.LINE_AA)

            # 5. Накладываем официальный логотип Prizolov.ru в верхнюю центральную часть баннера
            if self.logo_path.exists():
                logo = cv2.imread(str(self.logo_path), cv2.IMREAD_UNCHANGED)
                if logo is not None:
                    logo_res = cv2.resize(logo, (360, 90))
                    # Размещаем лого по центру сверху (Y: 40-130, X: 800-1160)
                    banner[40:130, 800:1160] = np.where(logo_res > 10, logo_res, banner[40:130, 800:1160])
            else:
                # Если файла логотипа нет, печатаем текстовый вотермарк Prizolov.ru
                cv2.putText(banner, "PRIZOLOV.RU", (800, 100), font, 1.5, (97, 211, 4), 3, cv2.LINE_AA)

            # Сохраняем готовый баннер на персистентный диск Amvera Cloud
            output_banner_path = self.data_dir / f"banners/promo_{match_id}.jpg"
            output_banner_path.parent.mkdir(parents=True, exist_ok=True)
            
            cv2.imwrite(str(output_banner_path), banner, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
            logger.info(f"[Media Poster] Графический баннер успешно сгенерирован и сохранен по пути: {output_banner_path}")
            return str(output_banner_path)

        except Exception as e:
            logger.error(f"Критический сбой генератора графических баннеров: {e}")
            return None
