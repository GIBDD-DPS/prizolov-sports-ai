# ============================================
# Prizolov Sports AI - Main System Orchestrator
# Version: 4.06 (Production Engine Optimization)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
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
from agent_bridge.client import PrizolovAgentClient
from modules.sentiment_miner import SentimentMinerModule
from modules.football import FootballAnalyticsModule
from modules.hockey import HockeyAnalyticsModule
from modules.basketball import BasketballAnalyticsModule
from modules.miscellaneous import MiscellaneousSportsModule

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PrizolovSportsAI.Orchestrator")

class PrizolovSportsOrchestrator:
    """Главный координатор системы нового поколения: интегрирован с событийными и сетевыми оптимизаторами"""

    def __init__(self, target_agent_host: Optional[str] = None):
        self.line_generator = BroadLineGenerator(default_margin=1.05)
        
        # Инжекция gRPC хоста: берем из переменной среды Amvera
        env_agent_host = os.getenv("AGENT_HOST", "localhost:50051")
        final_agent_host = target_agent_host if target_agent_host else env_agent_host
        
        self.agent_client = PrizolovAgentClient(target_host=final_agent_host)
        logger.info(f"[Env Sync] Настроен gRPC мост к Agent OS на адрес: {final_agent_host}")
        
        self.prematch_context = PreMatchContextModule()
        self.trend_predictor = MicroTrendPredictor(window_size_frames=1200)
        self.risk_manager = RiskManagementEngine(base_margin=1.05)
        
        # Оптимизированный сетевой компрессор трафика (версия 5.01)
        self.traffic_compressor = NetworkTrafficCompressor(odds_epsilon=0.02, coord_epsilon_meters=0.15)
        
        # Инжекция Redis хоста из переменных окружения Amvera Cloud
        redis_connection_string = os.getenv("REDIS_URL", None)
        self.sentiment_miner = SentimentMinerModule(
            min_capper_roi=5.0, 
            min_bets_count=100, 
            redis_url=redis_connection_string
        )
        
        self.active_module: Optional[Any] = None
        self.current_sport: Optional[str] = None
        self.match_id: Optional[str] = None
        self.is_initialized: bool = False
        self.match_metadata: Dict[str, Any] = {}
        
        self.calibrator: Optional[HomographyCalibrator] = None
        self.event_detector: Optional[SportsEventDetector] = None

    async def initialize_match(self, match_id: str, sport: str) -> None:
        """Динамическая инициализация матча с подключением к Redis кластеру и калибраторам"""
        self.match_id = match_id
        self.current_sport = sport.lower()
        
        # Активация пространственного калибратора и триггера событий
        self.calibrator = HomographyCalibrator(sport=self.current_sport)
        self.event_detector = SportsEventDetector(sport=self.current_sport)
        
        # Асинхронно активируем соединение с Managed Redis до старта трансляции
        await self.sentiment_miner.connect_redis()
        await self.agent_client.start()

        self.match_metadata = self.prematch_context.load_match_context(match_id, sport)
        calibrated_lambda_a, calibrated_lambda_b = self.prematch_context.get_calibrated_lambdas()

        try:
            await self.sentiment_miner.update_global_sentiment_trends()
        except Exception as e:
            logger.warning(f"Сбор сентимента завершился с предупреждением: {e}. Работа продолжена.")

        if self.current_sport == "football":
            self.active_module = FootballAnalyticsModule(match_id, self.line_generator)
            self.active_module.base_lambda_a = calibrated_lambda_a
            self.active_module.base_lambda_b = calibrated_lambda_b
        elif self.current_sport == "hockey":
            self.active_module = HockeyAnalyticsModule(match_id, self.line_generator)
            self.active_module.base_lambda_a = calibrated_lambda_a
            self.active_module.base_lambda_b = calibrated_lambda_b
        elif self.current_sport == "basketball":
            self.active_module = BasketballAnalyticsModule(match_id, self.line_generator)
            self.active_module.base_efficiency_a = calibrated_lambda_a / 1.5
            self.active_module.base_efficiency_b = calibrated_lambda_b / 1.5
        else:
            logger.info(f"Для вида спорта '{sport}' активирован универсальный адаптивный модуль.")
            self.active_module = MiscellaneousSportsModule(match_id, sport, self.line_generator)
            self.active_module.strength_factor_a = calibrated_lambda_a
            self.active_module.strength_factor_b = calibrated_lambda_b

        self.is_initialized = True
        logger.info(f"Матч {match_id} успешно оркестрован. Сервис Amvera Cloud готов к live-аналитике.")

    async def shutdown(self) -> None:
        """Корректное завершение работы оркестратора и деинициализация каналов связи"""
        self.is_initialized = False
        await self.agent_client.stop()
        logger.info("Ультимативный оркестратор Sports AI успешно остановлен.")

    def update_official_protocol(self, protocol_data: Dict[str, Any]) -> None:
        if not self.is_initialized or not self.active_module:
            return
        score_a = protocol_data.get("score_a", 0)
        score_b = protocol_data.get("score_b", 0)
        if self.current_sport == "football":
            self.active_module.set_match_state(score_a, score_b, protocol_data.get("corners_a", 0), protocol_data.get("corners_b", 0))
        elif self.current_sport == "hockey":
            self.active_module.set_match_state(score_a, score_b, protocol_data.get("shots_a", 0), protocol_data.get("shots_b", 0))
        elif self.current_sport == "basketball":
            self.active_module.set_match_state(score_a, score_b, protocol_data.get("fouls_a", 0), protocol_data.get("fouls_b", 0))
        else:
            self.active_module.set_match_state(score_a, score_b, protocol_data.get("extra_stat_a", 0), protocol_data.get("extra_stat_b", 0))

    async def process_cv_frame(self, tracking_data: Dict[str, Any], game_time_str: str, time_left_ratio: float, elapsed_seconds: int = 0) -> bool:
        if not self.is_initialized or not self.active_module:
            return False

        try:
            # Динамическая калибровка матрицы гомографии
            cv_img_pts = tracking_data.get("detected_pitch_pixel_points", [])
            if len(cv_img_pts) >= 4 and self.current_sport == "football":
                real_anchors = self.calibrator.get_static_football_pitch_anchors()
                self.calibrator.compute_matrix(cv_img_pts, real_anchors)

            # Трансформация пикселей мяча/шайбы в реальные метры поля через калибратор
            raw_bx = tracking_data.get("ball_x", 0.0)
            raw_by = tracking_data.get("ball_y", 0.0)
            
            if self.calibrator and self.calibrator.h_matrix is not None:
                raw_bx, raw_by = self.calibrator.transform_point(raw_bx, raw_by)
                tracking_data["ball_x"] = raw_bx
                tracking_data["ball_y"] = raw_by
                if "puck_x" in tracking_data:
                    tracking_data["puck_x"] = raw_bx
                    tracking_data["puck_y"] = raw_by

            # Новое: Анализ траектории на предмет голов/аутов с помощью EventDetector
            if self.event_detector:
                live_event = self.event_detector.analyze_ball_movement(raw_bx, raw_by)
                if live_event:
                    # При голе или ауте принудительно выставляем флаг заморозки игры для защиты от послеголов
                    tracking_data["is_game_stopped"] = True

            current_frame_metrics = {
                "possession_a": tracking_data.get("recent_dominance_ratio", 0.5) * 100.0,
                "xg_a": tracking_data.get("live_xg_a", 0.0),
                "xg_b": tracking_data.get("live_xg_b", 0.0),
                "dangerous_attacks_a": tracking_data.get("danger_attacks_a", 0),
                "dangerous_attacks_b": tracking_data.get("danger_attacks_b", 0)
            }
            self.trend_predictor.update_metrics_history(current_frame_metrics)

            press_multiplier_a, press_multiplier_b = self.trend_predictor.predict_next_interval_pressure()
            tracking_data["live_xg_a"] *= press_multiplier_a
            tracking_data["live_xg_b"] *= press_multiplier_b

            if elapsed_seconds > 0 and elapsed_seconds % 60 == 0:
                asyncio.create_task(self.sentiment_miner.update_global_sentiment_trends())

            is_critical = tracking_data.get("is_game_stopped", False) or (press_multiplier_a > 1.8 or press_multiplier_b > 1.8)
            dyn_margin = self.risk_manager.adjust_margin_by_volatility(
                live_xg_speed=max(press_multiplier_a, press_multiplier_b) - 1.0,
                is_critical_moment=is_critical
            )
            self.line_generator.margin = dyn_margin

            if self.current_sport == "basketball":
                analytics_package = self.active_module.process_frame_data(tracking_data, game_time_str, time_left_ratio, elapsed_seconds)
            else:
                analytics_package = self.active_module.process_frame_data(tracking_data, game_time_str, time_left_ratio)

            team_a = self.match_metadata.get("team_name_a", "TeamA")
            team_b = self.match_metadata.get("team_name_b", "TeamB")
            
            for market_group in ["main_outcomes", "totals", "active_specials"]:
                if market_group in analytics_package["line_data"]:
                    for outcome in analytics_package["line_data"][market_group]:
                        sentiment_mod = await self.sentiment_miner.get_market_sentiment_modifier(team_a, team_b, outcome["market_name"])
                        if sentiment_mod > 1.0:
                            outcome["odds"] = round(outcome["odds"] / (sentiment_mod * 0.98), 2)

            competitor_mock_feed = tracking_data.get("competitor_odds_feed", {})
            analytics_package["line_data"] = self.risk_manager.apply_anti_arbitrage_filter(
                our_line=analytics_package["line_data"],
                market_feed_odds=competitor_mock_feed
            )

            # Новое: Дедупликация и фильтрация лишнего трафика перед физической gRPC отправкой
            if self.traffic_compressor.should_skip_frame(analytics_package):
                # Если изменения незначительны — экономим битрейт Amvera Cloud и не шлем дубликат
                return True

            success = await self.agent_client.push_match_data(analytics_package)
            return success

        except Exception as e:
            logger.error(f"Критический сбой в ультимативном пайплайне оркестратора: {e}")
            return False
