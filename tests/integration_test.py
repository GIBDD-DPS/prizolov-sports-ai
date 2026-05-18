# ============================================
# Prizolov Sports AI - Automated Integration Tests
# Version: 5.01 (Initial Architecture Release)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production CI/CD validation code
# ============================================

import sys
import os
import asyncio
from pathlib import Path

# Жесткое прописывание путей для запуска тестов из любого контекста
current_dir = Path(__file__).resolve().parent
root_dir = current_dir.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "agent_bridge"))

import unittest
from core.line_generator import BroadLineGenerator
from core.trend_predictor import MicroTrendPredictor
from core.risk_manager import RiskManagementEngine
from modules.sentiment_miner import SentimentMinerModule
import agent_bridge.prizolov_agent_pb2 as pb2


class TestPrizolovSportsAI(unittest.TestCase):
    """Комплексный тестовый сьют для валидации математических и логических ядер ИИ"""

    def setUp(self):
        """Инициализация тестируемых модулей перед каждым тестом"""
        self.line_gen = BroadLineGenerator(default_margin=1.05)
        self.risk_eng = RiskManagementEngine(base_margin=1.05)
        self.trend_pred = MicroTrendPredictor(window_size_frames=10)
        self.sentiment_miner = SentimentMinerModule(min_capper_roi=5.0, min_bets_count=10)

    def test_poisson_line_generator_math(self):
        """Проверяет корректность расчета букмекерских коэффициентов по Пуассону"""
        # Симулируем футбольный матч: 75-я минута, счет 1:0, умеренная атака
        res = self.line_gen.calculate_poisson_line(
            lambda_team_a=1.5,
            lambda_team_b=1.0,
            time_left_ratio=0.16,  # ~15 минут до конца матча
            current_score_a=1,
            current_score_b=0
        )
        
        self.assertIn("main_outcomes", res)
        self.assertIn("totals", res)
        
        # Проверяем, что маркеты содержат валидные коэффициенты (> 1.0)
        for outcome in res["main_outcomes"]:
            self.assertGreater(outcome["odds"], 1.0)
            self.assertFalse(outcome["is_suspended"])

    def test_high_score_line_generator_math(self):
        """Проверяет корректность расчета линий для баскетбола по нормальной аппроксимации"""
        res = self.line_gen.calculate_high_score_line(
            pace=80.0,
            efficiency_a=1.05,
            efficiency_b=1.02,
            time_left_ratio=0.5,  # Половина матча
            current_score_a=45,
            current_score_b=42
        )
        
        self.assertIn("main_outcomes", res)
        self.assertIn("totals", res)
        
        # Коэффициенты на победителя матча 1 или 2 в баскетболе должны быть строго валидными
        self.assertEqual(len(res["main_outcomes"]), 2)
        self.assertGreater(res["main_outcomes"][0]["odds"], 1.0)

    def test_risk_manager_volatility_brake(self):
        """Проверяет динамическое увеличение маржи при всплеске Live-волатильности"""
        # Обычный момент: маржа базовая
        margin_normal = self.risk_eng.adjust_margin_by_volatility(live_xg_speed=0.01, is_critical_moment=False)
        self.assertEqual(margin_normal, 1.05)
        
        # Критический live-момент (пенальти или опасная атака): маржа должна вырасти для страховки
        margin_critical = self.risk_eng.adjust_margin_by_volatility(live_xg_speed=0.25, is_critical_moment=True)
        self.assertGreater(margin_critical, margin_normal)

    def test_trend_predictor_rolling_buffer(self):
        """Проверяет работу скользящего окна памяти трендов без утечек"""
        for i in range(15):  # Пушим 15 кадров в буфер размером 10
            self.trend_pred.update_metrics_history({
                "possession_a": 55.0,
                "xg_a": 0.05 * i,
                "xg_b": 0.01
            })
            
        # Проверяем удержание жесткого лимита скользящего окна
        self.assertEqual(len(self.trend_pred.history_possession_a), 10)

    def test_sentiment_miner_antiban_nlp(self):
        """Проверяет базовую логику лингвистического скоринга текста прогнозов"""
        text_confident = "Это железная ставка, зайдет легко, уверен на все сто."
        text_risky = "Сложный матч, высокий риск, играть очень аккуратно."
        
        score_confident = self.sentiment_miner._nlp_analyze_intent(text_confident)
        score_risky = self.sentiment_miner._nlp_analyze_intent(text_risky)
        
        # Уверенный текст должен получить более высокий балл ИИ, чем сомнительный
        self.assertGreater(score_confident, score_risky)


if __name__ == "__main__":
    unittest.main()
