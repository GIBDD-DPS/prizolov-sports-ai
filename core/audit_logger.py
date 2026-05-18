# ============================================
# Prizolov Sports AI - Security Audit Logger
# Version: 5.01 (Initial Architecture Release)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production Security & Fraud Protection
# ============================================

import sys
import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger("PrizolovSportsAI.Audit")

class SportsAuditLogger:
    """Модуль фиксации аномалий, рисков и live-действий скаутов для аудита безопасности"""

    def __init__(self, match_id: str, base_data_dir: str = "/data"):
        self.match_id = match_id
        self.log_dir = Path(base_data_dir) / "audit"
        self.log_file = self.log_dir / f"audit_{self.match_id}.log"
        
        # Гарантируем физическое существование директории на постоянном диске
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Не удалось создать директорию логов аудита: {e}. Фолбэк в корень.")
            self.log_file = Path(f"audit_{self.match_id}.log")

    def log_anomaly(self, anomaly_type: str, severity: str, details: Dict[str, Any]) -> None:
        """
        Записывает структурированное событие аномалии или риска в JSON-Live формате.
        Типы: 'SUSPEND_TOGGLE', 'XG_SPIKE', 'ARBITRAGE_DETECTED', 'PROTOCOL_MISMATCH'
        """
        audit_entry = {
            "timestamp_ms": int(time.time() * 1000),
            "match_id": self.match_id,
            "anomaly_type": anomaly_type.upper(),
            "severity": severity.upper(), # 'INFO', 'WARNING', 'CRITICAL'
            "details": details
        }
        
        try:
            # Используем атомарную дозапись в конец файла (Thread-safe)
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(audit_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Ошибка записи в журнал аудита безопасности: {e}")

    def check_xg_anomaly(self, last_xg: float, current_xg: float, threshold: float = 0.35) -> None:
        """Автоматически детектирует аномальный скачок xG между кадрами (возможен гол)"""
        diff = current_xg - last_xg
        if diff > threshold:
            self.log_anomaly(
                anomaly_type="XG_SPIKE",
                severity="WARNING",
                details={
                    "previous_xg": round(last_xg, 3),
                    "current_xg": round(current_xg, 3),
                    "delta": round(diff, 3),
                    "message": "Зафиксировано взрывное нарастание xG. Возможна задержка live-фида."
                }
            )
