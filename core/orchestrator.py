# ============================================
# Prizolov Sports AI - Main System Orchestrator
# Version: 5.01 (Multi-Match Registry Core)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production Multi-Stream Deployment at prizolov.ru
# ============================================

import sys
import os
from pathlib import Path

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import asyncio
import logging
from typing import Dict, Any, Optional

from core.line_generator import BroadLineGenerator
from core.prematch_context import PreMatchContextModule
from core.trend_predictor import MicroTrendPredictor
from core.risk_manager import RiskManagementEngine
from core.homography_calibrator import HomographyCalibrator
from core.event_detector import SportsEventDetector
from core.traffic_compressor import NetworkTrafficCompressor
from core.line_change_analyser import LineChangeAnalyser
from core.fallback_db import LocalFallbackDB
from core.lens_calibrator import LensDistortionCalibrator
from core.occlusion_filter import TrackingOcclusionFilter
from core.memory_balancer import ProductionMemoryBalancer
from core.staff_filter import RefereeStaffFilter
from core.stream_validator import StreamQualityValidator
from core.weather_analytics import WeatherAnalyticsEngine
from core.time_synchronizer import OpticalTimeSynchronizer
from core.ball_validator import BallPuckValidator
from core.video_flicker_filter import AntiFlickerVideoFilter
from core.referee_analytics import RefereeSeverityAnalytics
from core.lens_noise_filter import LensNoiseFilter
from modules.text_inference import LiveTextInferenceEngine

from agent_bridge.client import PrizolovAgentClient
from agent_bridge.web_proxy import gRPCWebProxyConnector
from modules.sentiment_miner import SentimentMinerModule
from modules.football import FootballAnalyticsModule
from modules.hockey import HockeyAnalyticsModule
from modules.basketball import BasketballAnalyticsModule
from modules.miscellaneous import MiscellaneousSportsModule

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PrizolovSportsAI.Orchestrator")

class PrizolovSportsOrchestrator:
    """Глобальный Enterprise-координатор кластера: параллельно обрабатывает множество live-матчей без перекрестных утечек памяти"""

    def __init__(self, target_agent_host: Optional[str] = None):
        self.line_generator = BroadLineGenerator(default_margin=1.05)
        
        env_agent_host = os.getenv("AGENT_HOST", "localhost:50051")
        final_agent_host = target_agent_host if target_agent_host else env_agent_host
        
        self.agent_client = PrizolovAgentClient(target_host=final_agent_host)
        logger.info(f"[Cluster Sync] Сетевой gRPC мост запущен к Agent OS на: {final_agent_host}")
        
        self.web_proxy = gRPCWebProxyConnector()
        self.risk_manager = RiskManagementEngine(base_margin=1.05)
        self.fallback_db = LocalFallbackDB(base_data_dir=os.getenv("PERSISTENT_DATA_DIR", "/data"))
        self.memory_balancer = ProductionMemoryBalancer(max_allowed_ram_mb=1540.0, force_gc_interval_frames=1200)
        
        # Новое: Глобальный реестр активных live-матчей для реализации мультиканальности
        # Структура: {match_id: { "sport": str, "module": Any, "calibrator": Any, "validator": Any, ... }}
        self.active_matches_registry: Dict[str, Dict[str, Any]] = {}

        redis_connection_string = os.getenv("REDIS_URL", None)
        self.sentiment_miner = SentimentMinerModule(
            min_capper_roi=5.0, 
            min_bets_count=100, 
            redis_url=redis_connection_string
        )

    async def initialize_match(self, match_id: str, sport: str) -> None:
        """Регистрирует и изолированно инициализирует новый матч в пуле мультиканальности"""
        sport_key = sport.lower()
        
        # Если матч уже в реестре, предотвращаем дублирование инициализации
        if match_id in self.active_matches_registry:
            logger.warning(f"[Cluster Registry] Матч {match_id} уже запущен в рантайме. Пропуск.")
            return

        # Поднимаем индивидуальный защищенный gRPC/Redis транспорт при первом старте реестра
        if not self.active_matches_registry:
            await self.sentiment_miner.connect_redis()
            await self.agent_client.start()

        prematch_context = PreMatchContextModule()
        match_metadata = prematch_context.load_match_context(match_id, sport_key)
        calibrated_lambda_a, calibrated_lambda_b = prematch_context.get_calibrated_lambdas()

        # Инициализируем персональные модули компьютерного зрения и NLP под данный матч
        line_change_analyser = LineChangeAnalyser(sport=sport_key)
        mock_weights_a = {"97": 1.4, "87": 1.3, "10": 1.1}
        mock_weights_b = {"99": 1.5, "13": 1.2, "77": 0.9}
        line_change_analyser.load_player_weights(mock_weights_a, mock_weights_b)

        if sport_key == "football":
            active_module = FootballAnalyticsModule(match_id, self.line_generator)
            active_module.base_lambda_a = calibrated_lambda_a
            active_module.base_lambda_b = calibrated_lambda_b
        elif sport_key == "hockey":
            active_module = HockeyAnalyticsModule(match_id, self.line_generator)
            active_module.base_lambda_a = calibrated_lambda_a
            active_module.base_lambda_b = calibrated_lambda_b
        elif sport_key == "basketball":
            active_module = BasketballAnalyticsModule(match_id, self.line_generator)
            active_module.base_efficiency_a = calibrated_lambda_a / 1.5
            active_module.base_efficiency_b = calibrated_lambda_b / 1.5
        else:
            active_module = MiscellaneousSportsModule(match_id, sport_key, self.line_generator)
            active_module.strength_factor_a = calibrated_lambda_a
            active_module.strength_factor_b = calibrated_lambda_b

        # Упаковываем все контекстные ИИ-процессоры в изолированную ячейку реестра
        self.active_matches_registry[match_id] = {
            "sport": sport_key,
            "module": active_module,
            "metadata": match_metadata,
            "calibrator": HomographyCalibrator(sport=sport_key),
            "event_detector": SportsEventDetector(sport=sport_key),
            "line_change": line_change_analyser,
            "lens_calibrator": LensDistortionCalibrator(img_width=1920, img_height=1080),
            "ball_validator": BallPuckValidator(sport=sport_key, fps=25.0),
            "flicker_filter": AntiFlickerVideoFilter(rolling_window_size=15),
            "staff_filter": RefereeStaffFilter(),
            "stream_validator": StreamQualityValidator(freeze_threshold_mse=0.5, max_freeze_frames=40),
            "weather": WeatherAnalyticsEngine(),
            "time_sync": OpticalTimeSynchronizer(scorebug_crop_coords=(20, 40, 180, 80)),
            "text_nlp": LiveTextInferenceEngine(match_id=match_id),
            "trend_predictor": MicroTrendPredictor(window_size_frames=1200),
            "traffic_compressor": NetworkTrafficCompressor(odds_epsilon=0.02, coord_epsilon_meters=0.15)
        }
        
        # Загружаем стартовые метеорологические параметры для данной локации
        self.active_matches_registry[match_id]["weather"].load_match_weather_report({"condition": "CLEAR", "wind_speed": 2.0, "temperature": 18.0})
        self.active_matches_registry[match_id]["time_sync"].last_valid_seconds = 0

        logger.info(f"[Cluster Registry] Матч {match_id} успешно добавлен в пул мультиканальности. Всего в обработке: {len(self.active_matches_registry)}")

    async def shutdown(self) -> None:
        """Полная деинициализация пула матчей и закрытие транспорта"""
        self.active_matches_registry.clear()
        await self.agent_client.stop()
        logger.info("Ультимативный многопоточный оркестратор кластера успешно остановлен.")

    def update_official_protocol(self, match_id: str, protocol_data: Dict[str, Any]) -> None:
        """Маршрутизирует обновление судейского протокола в конкретную ячейку матча"""
        ctx = self.active_matches_registry.get(match_id)
        if not ctx:
            return
            
        score_a = protocol_data.get("score_a", 0)
        score_b = protocol_data.get("score_b", 0)
        sport = ctx["sport"]
        
        if sport == "football":
            ctx["module"].set_match_state(score_a, score_b, protocol_data.get("corners_a", 0), protocol_data.get("corners_b", 0))
        elif sport == "hockey":
            ctx["module"].set_match_state(score_a, score_b, protocol_data.get("shots_a", 0), protocol_data.get("shots_b", 0))
        elif sport == "basketball":
            ctx["module"].set_match_state(score_a, score_b, protocol_data.get("fouls_a", 0), protocol_data.get("fouls_b", 0))
        else:
            ctx["module"].set_match_state(score_a, score_b, protocol_data.get("extra_stat_a", 0), protocol_data.get("extra_stat_b", 0))

    async def process_cv_frame(self, match_id: str, tracking_data: Dict[str, Any], game_time_str: str, time_left_ratio: float, elapsed_seconds: int = 0) -> bool:
        """
        Главный высокопроизводительный распределенный конвейер обработки кадра.
        Все вычисления жестко изолированы по ключу match_id.
        """
        ctx = self.active_matches_registry.get(match_id)
        if not ctx:
            return False

        try:
            # 1. Попиксельная проверка фризов и оптическая стабилизация кадра
            if "raw_video_frame" in tracking_data:
                tracking_data["raw_video_frame"] = ctx["flicker_filter"].process_and_stabilize_light(tracking_data["raw_video_frame"])
                if not ctx["stream_validator"].check_stream_integrity(tracking_data["raw_video_frame"]) or ctx["stream_validator"].is_stream_broken:
                    tracking_data["is_game_stopped"] = True

                # Оптическая синхронизация игровых часов через OCR
                ocr_seconds = ctx["time_sync"].sync_time_by_ocr(tracking_data["raw_video_frame"])
                if ocr_seconds is not None and ocr_seconds > 0:
                    elapsed_seconds = ocr_seconds
                    total_match_seconds = 5400 if ctx["sport"] == "football" else (3600 if ctx["sport"] == "hockey" else 2400)
                    time_left_ratio = max(0.0, 1.0 - (elapsed_seconds / total_match_seconds))
                    game_time_str = f"{elapsed_seconds // 60:02d}:{elapsed_seconds % 60:02d}"

            # 2. Асинхронный контекстный NLP-анализ текстовых фидов
            if elapsed_seconds % 6 == 0:
                nlp_event = await ctx["text_nlp"].poll_live_text_feed()
                if nlp_event:
                    intent, details = nlp_event
                    if intent == "VAR_REVIEW":
                        tracking_data["is_game_stopped"] = True
                    elif intent == "INJURY" and hasattr(ctx["module"], "base_lambda_a"):
                        ctx["module"].base_lambda_a *= details["impact_factor"]
                        ctx["module"].base_lambda_b *= details["impact_factor"]

            raw_bx = tracking_data.get("ball_x", 0.0)
            raw_by = tracking_data.get("ball_y", 0.0)
            
            # 3. Аппаратная компенсация искажений объектива и запуск гомографии
            if ctx["lens_calibrator"].is_calibrated:
                raw_bx, raw_by = ctx["lens_calibrator"].undistort_points(raw_bx, raw_by)
                if "detected_pitch_pixel_points" in tracking_data:
                    tracking_data["detected_pitch_pixel_points"] = [
                        ctx["lens_calibrator"].undistort_points(pt, pt) for pt in tracking_data["detected_pitch_pixel_points"]
                    ]

            cv_img_pts = tracking_data.get("detected_pitch_pixel_points", [])
            if len(cv_img_pts) >= 4 and ctx["sport"] == "football":
                ctx["calibrator"].compute_matrix(cv_img_pts, ctx["calibrator"].get_static_football_pitch_anchors())

            if ctx["calibrator"].h_matrix is not None:
                raw_bx, raw_by = ctx["calibrator"].transform_point(raw_bx, raw_by)

            # 4. Физическая валидация траектории мяча/шайбы
            is_ball_found = "ball_x" in tracking_data and "ball_y" in tracking_data
            valid_bx, valid_by, is_active_ball = ctx["ball_validator"].validate_and_smooth_trajectory(raw_bx, raw_by, is_found_by_yolo=is_ball_found)
            tracking_data["ball_x"] = valid_bx
            tracking_data["ball_y"] = valid_by

            # 5. Очистка шумов: Удаление судей из кадра и фильтрация 3D-окклюзий
            if "raw_player_detections" in tracking_data and "raw_video_frame" in tracking_data:
                tracking_data["raw_player_detections"] = ctx["staff_filter"].filter_active_players(tracking_data["raw_player_detections"], tracking_data["raw_video_frame"])
            if "raw_player_detections" in tracking_data:
                tracking_data["raw_player_detections"] = ctx["occlusion_filter"].filter_occlusions(tracking_data["raw_player_detections"])

            # 6. Анализ звеньев и климатический демпинг интенсивностей
            obs_num_a = tracking_data.get("ocr_jersey_numbers_team_a", [])
            obs_num_b = tracking_data.get("ocr_jersey_numbers_team_b", [])
            strength_idx_a, strength_idx_b = ctx["line_change"].update_observed_players(obs_num_a, obs_num_b)
            
            w_decay_a, w_decay_b = ctx["weather"].calculate_weather_decay_modifiers()
            
            if hasattr(ctx["module"], "base_lambda_a"):
                ctx["module"].base_lambda_a *= (strength_idx_a * w_decay_a)
                ctx["module"].base_lambda_b *= (strength_idx_b * w_decay_b)

            if ctx["event_detector"] and is_active_ball:
                if ctx["event_detector"].analyze_ball_movement(valid_bx, valid_by):
                    tracking_data["is_game_stopped"] = True

            # 7. Расчет xG давления и генерация широкой линии
            current_frame_metrics = {
                "possession_a": tracking_data.get("recent_dominance_ratio", 0.5) * 100.0,
                "xg_a": tracking_data.get("live_xg_a", 0.0), "xg_b": tracking_data.get("live_xg_b", 0.0),
                "dangerous_attacks_a": tracking_data.get("danger_attacks_a", 0), "dangerous_attacks_b": tracking_data.get("danger_attacks_b", 0)
            }
            ctx["trend_predictor"].update_metrics_history(current_frame_metrics)
            press_multiplier_a, press_multiplier_b = ctx["trend_predictor"].predict_next_interval_pressure()
            tracking_data["live_xg_a"] *= press_multiplier_a
            tracking_data["live_xg_b"] *= press_multiplier_b

            is_critical = tracking_data.get("is_game_stopped", False) or (press_multiplier_a > 1.8 or press_multiplier_b > 1.8)
            self.line_generator.margin = self.risk_manager.adjust_margin_by_volatility(max(press_multiplier_a, press_multiplier_b) - 1.0, is_critical)

            if ctx["sport"] == "basketball":
                analytics_package = ctx["module"].process_frame_data(tracking_data, game_time_str, time_left_ratio, elapsed_seconds)
            else:
                analytics_package = ctx["module"].process_frame_data(tracking_data, game_time_str, time_left_ratio)

            # 8. Наложение капперского NLP-сентимента и анти-вилочного фильтра рисков
            team_a = ctx["metadata"].get("team_name_a", "TeamA")
            team_b = ctx["metadata"].get("team_name_b", "TeamB")
            for market_group in ["main_outcomes", "totals", "active_specials"]:
                if market_group in analytics_package["line_data"]:
                    for outcome in analytics_package["line_data"][market_group]:
                        sentiment_mod = await self.sentiment_miner.get_market_sentiment_modifier(team_a, team_b, outcome["market_name"])
                        if sentiment_mod > 1.0: outcome["odds"] = round(outcome["odds"] / (sentiment_mod * 0.98), 2)

            analytics_package["line_data"] = self.risk_manager.apply_anti_arbitrage_filter(analytics_package["line_data"], tracking_data.get("competitor_odds_feed", {}))

            if ctx["stream_validator"].is_stream_broken:
                for group in ["main_outcomes", "totals", "handicaps"]:
                    if group in analytics_package["line_data"]:
                        for outcome in analytics_package["line_data"][group]: outcome["is_suspended"] = True

            # 9. Эпсилон-фильтрация и пуш в транспортные WebSocket и gRPC каналы
            if ctx["traffic_compressor"].should_skip_frame(analytics_package):
                return True

            if not self.agent_client.is_running:
                self.fallback_db.buffer_package(match_id, analytics_package)
                return False

            # Прямой форвард готового live-пакета в WebSocket менеджер вещания для фронтенда prizolov.ru
            from core.admin_dashboard import ws_manager
            await ws_manager.broadcast_live_package(analytics_package)

            success = await self.agent_client.push_match_data(analytics_package)
            self.memory_balancer.balance_resources()
            return success

        except Exception as e:
            logger.error(f"Критический сбой распределенного конвейера для матча {match_id}: {e}")
            return False
