# ============================================
# Prizolov Sports AI - Main System Orchestrator
# Version: 4.09 (Production Scaled Runtime)
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
from core.line_change_analyser import LineChangeAnalyser
from core.fallback_db import LocalFallbackDB
from core.lens_calibrator import LensDistortionCalibrator
from core.occlusion_filter import TrackingOcclusionFilter
from core.memory_balancer import ProductionMemoryBalancer
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
    """Главный координатор системы нового поколения: интегрирован с фильтрацией окклюзий и защитой RAM"""

    def __init__(self, target_agent_host: Optional[str] = None):
        self.line_generator = BroadLineGenerator(default_margin=1.05)
        
        env_agent_host = os.getenv("AGENT_HOST", "localhost:50051")
        final_agent_host = target_agent_host if target_agent_host else env_agent_host
        
        self.agent_client = PrizolovAgentClient(target_host=final_agent_host)
        logger.info(f"[Env Sync] Настроен gRPC мост к Agent OS на адрес: {final_agent_host}")
        
        self.web_proxy = gRPCWebProxyConnector()
        self.prematch_context = PreMatchContextModule()
        self.trend_predictor = MicroTrendPredictor(window_size_frames=1200)
        self.risk_manager = RiskManagementEngine(base_margin=1.05)
        self.traffic_compressor = NetworkTrafficCompressor(odds_epsilon=0.02, coord_epsilon_meters=0.15)
        self.fallback_db = LocalFallbackDB(base_data_dir=os.getenv("PERSISTENT_DATA_DIR", "/data"))
        
        # Новое: Активация 3D-фильтра окклюзий и системного балансировщика оперативной памяти (версии 5.01)
        self.occlusion_filter = TrackingOcclusionFilter(overlap_threshold=0.55)
        self.memory_balancer = ProductionMemoryBalancer(max_allowed_ram_mb=1540.0, force_gc_interval_frames=1200)
        
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
        self.line_change_analyser: Optional[LineChangeAnalyser] = None
        self.lens_calibrator: Optional[LensDistortionCalibrator] = None

    async def initialize_match(self, match_id: str, sport: str) -> None:
        """Динамическая инициализация матча с подключением к Redis кластеру и калибраторам"""
        self.match_id = match_id
        self.current_sport = sport.lower()
        
        self.calibrator = HomographyCalibrator(sport=self.current_sport)
        self.event_detector = SportsEventDetector(sport=self.current_sport)
        self.line_change_analyser = LineChangeAnalyser(sport=self.current_sport)
        self.lens_calibrator = LensDistortionCalibrator(img_width=1920, img_height=1080)
        
        await self.sentiment_miner.connect_redis()
        await self.agent_client.start()

        self.match_metadata = self.prematch_context.load_match_context(match_id, sport)
        calibrated_lambda_a, calibrated_lambda_b = self.prematch_context.get_calibrated_lambdas()

        mock_weights_a = {"97": 1.4, "87": 1.3, "10": 1.1}
        mock_weights_b = {"99": 1.5, "13": 1.2, "77": 0.9}
        self.line_change_analyser.load_player_weights(mock_weights_a, mock_weights_b)

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
            raw_bx = tracking_data.get("ball_x", 0.0)
            raw_by = tracking_data.get("ball_y", 0.0)
            
            # Аппаратная компенсация оптической дисторсии «рыбьего глаза»
            if self.lens_calibrator and self.lens_calibrator.is_calibrated:
                raw_bx, raw_by = self.lens_calibrator.undistort_points(raw_bx, raw_by)
                if "detected_pitch_pixel_points" in tracking_data:
                    tracking_data["detected_pitch_pixel_points"] = [
                        self.lens_calibrator.undistort_points(pt[0], pt[1]) for pt in tracking_data["detected_pitch_pixel_points"]
                    ]

            # Динамическая калибровка матрицы гомографии
            cv_img_pts = tracking_data.get("detected_pitch_pixel_points", [])
            if len(cv_img_pts) >= 4 and self.current_sport == "football":
                real_anchors = self.calibrator.get_static_football_pitch_anchors()
                self.calibrator.compute_matrix(cv_img_pts, real_anchors)

            # Трансформация выпрямленных пикселей в метры поля
            if self.calibrator and self.calibrator.h_matrix is not None:
                raw_bx, raw_by = self.calibrator.transform_point(raw_bx, raw_by)
                tracking_data["ball_x"] = raw_bx
                tracking_data["ball_y"] = raw_by

            # Новое: Продвинутая 3D-фильтрация окклюзий и взаимных перекрытий силуэтов игроков в кадре
            if "raw_player_detections" in tracking_data:
                tracking_data["raw_player_detections"] = self.occlusion_filter.filter_occlusions(
                    tracking_data["raw_player_detections"]
                )

            if self.line_change_analyser:
                obs_num_a = tracking_data.get("ocr_jersey_numbers_team_a", [])
                obs_num_b = tracking_data.get("ocr_jersey_numbers_team_b", [])
                strength_idx_a, strength_idx_b = self.line_change_analyser.update_observed_players(obs_num_a, obs_num_b)
                if hasattr(self.active_module, "base_lambda_a"):
                    self.active_module.base_lambda_a *= strength_idx_a
                    self.active_module.base_lambda_b *= strength_idx_b

            if self.event_detector:
                live_event = self.event_detector.analyze_ball_movement(raw_bx, raw_by)
                if live_event:
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

            if self.traffic_compressor.should_skip_frame(analytics_package):
                return True

            if not self.agent_client.is_running:
                self.fallback_db.buffer_package(self.match_id, analytics_package)
                return False

            success = await self.agent_client.push_match_data(analytics_package)
            
            try:
                _ = self.web_proxy.encode_grpc_web_frame(self.agent_client.stub.StreamMatchAnalytics)
            except Exception:
                pass

            if success and elapsed_seconds % 30 == 0:
                buffered = self.fallback_db.fetch_buffered_packages(limit=20)
                if buffered:
                    self.fallback_db.clear_buffered_packages([b[0] for b in buffered])

            # Новое: Вызов менеджера контроля оперативной памяти в конце каждого кадра
            self.memory_balancer.balance_resources()

            return success

        except Exception as e:
            logger.error(f"Критический сбой в ультимативном пайплайне оркестратора: {e}")
            return False
