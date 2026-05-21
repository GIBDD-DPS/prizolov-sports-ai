# ============================================
# Prizolov Sports AI - Traffic Compressor
# Version: 5.02 (Strict Import Alignment)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: High-Performance Network Optimization
# ============================================

import sys
import os
import zlib
import math
# Исправлено: Добавлен нативный импорт Path для полной ликвидации NameError в Amvera
from pathlib import Path
from typing import Dict, Any, Optional, List

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

class NetworkTrafficCompressor:
    """Модуль дедупликации фреймов широкой линии и бинарного сжатия трафика к Agent OS"""

    def __init__(self, odds_epsilon: float = 0.02, coord_epsilon_metrics: float = 0.15):
        self.odds_eps = odds_epsilon
        self.coord_eps = coord_epsilon_metrics
        self.last_sent_package: Optional[Dict[str, Any]] = None

    def _is_odds_diff_negligible(self, old_markets: List[Dict[str, Any]], new_markets: List[Dict[str, Any]]) -> bool:
        """Проверяет, изменились ли букмекерские коэффициенты выше порога чувствительности"""
        if len(old_markets) != len(new_markets):
            return False
            
        for old, new in zip(old_markets, new_markets):
            if old.get("market_name") != new.get("market_name"):
                return False
            if old.get("is_suspended") != new.get("is_suspended"):
                return False
            if abs(old.get("odds", 0.0) - new.get("odds", 0.0)) > self.odds_eps:
                return False
        return True

    def should_skip_frame(self, current_package: Dict[str, Any]) -> bool:
        """Реализует алгоритм дедупликации фреймов для экономии битрейта"""
        if self.last_sent_package is None:
            self.last_sent_package = current_package
            return False

        old_ball = self.last_sent_package.get("ball_state", {})
        new_ball = current_package.get("ball_state", {})
        
        dist = math.sqrt((old_ball.get("x", 0.0) - new_ball.get("x", 0.0))**2 + 
                         (old_ball.get("y", 0.0) - new_ball.get("y", 0.0))**2)
                         
        if dist > self.coord_eps:
            self.last_sent_package = current_package
            return False

        old_line = self.last_sent_package.get("line_data", {})
        new_line = current_package.get("line_data", {})
        
        for market_key in ["main_outcomes", "totals", "handicaps"]:
            if not self._is_odds_diff_negligible(old_line.get(market_key, []), new_line.get(market_key, [])):
                self.last_sent_package = current_package
                return False

        return True

    def compress_payload(self, string_data: str) -> bytes:
        """Сжимает строковые JSON метаданные в плотный бинарный буфер"""
        if not string_data:
            return b""
        return zlib.compress(string_data.encode('utf-8'), level=9)

    def decompress_payload(self, compressed_bytes: bytes) -> str:
        """Распаковывает бинарный буфер обратно в исходную JSON строку"""
        if not compressed_bytes:
            return ""
        return zlib.decompress(compressed_bytes).decode('utf-8')
