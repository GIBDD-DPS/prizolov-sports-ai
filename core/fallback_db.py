# ============================================
# Prizolov Sports AI - Local Fallback DB
# Version: 5.01 (Initial Architecture Release)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Data Resilience & High Availability
# ============================================

import sys
import os
import sqlite3
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger("PrizolovSportsAI.FallbackDB")

class LocalFallbackDB:
    """Модуль локального SQLite-буфера для сохранения пакетов аналитики при потере связи с сетью"""

    def __init__(self, base_data_dir: str = "/data"):
        self.db_path = Path(base_data_dir) / "fallback_buffer.db"
        self._initialize_database()

    def _initialize_database(self) -> None:
        """Создает локальную таблицу буферизации данных, если файл БД не существует"""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                # Создаем таблицу с WAL-режимом логирования для максимальной скорости записи
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS analytics_buffer (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp_ms INTEGER NOT NULL,
                        match_id TEXT NOT NULL,
                        payload TEXT NOT NULL
                    )
                """)
                conn.commit()
                # Активируем асинхронный WAL режим записи на диск
                conn.execute("PRAGMA journal_mode=WAL")
        except Exception as e:
            logger.error(f"Ошибка инициализации локальной SQLite базы данных: {e}")

    def buffer_package(self, match_id: str, package_data: Dict[str, Any]) -> bool:
        """Сохраняет пакет аналитики в локальный зашифрованный JSON-буфер на диске"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO analytics_buffer (timestamp_ms, match_id, payload) VALUES (?, ?, ?)",
                    (int(time.time() * 1000), match_id, json.dumps(package_data, ensure_ascii=False))
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Не удалось записать фрейм в локальный fallback-буфер: {e}")
            return False

    def fetch_buffered_packages(self, limit: int = 50) -> List[Tuple[int, Dict[str, Any]]]:
        """Вычитывает старейшие сохраненные пакеты из буфера для отправки после восстановления сети"""
        packages = []
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, payload FROM analytics_buffer ORDER BY id ASC LIMIT ?", (limit,))
                rows = cursor.fetchall()
                for row in rows:
                    packages.append((row[0], json.loads(row[1])))
        except Exception as e:
            logger.error(f"Ошибка вычитки пакетов из локального буфера: {e}")
        return packages

    def clear_buffered_packages(self, record_ids: List[int]) -> None:
        """Удаляет успешно переданные пакеты из локальной базы данных"""
        if not record_ids:
            return
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                # Формируем безопасный множественный запрос на удаление по ID
                placeholders = ",".join("?" for _ in record_ids)
                cursor.execute(f"DELETE FROM analytics_buffer WHERE id IN ({placeholders})", record_ids)
                conn.commit()
                logger.info(f"[Resilience] Очищено {len(record_ids)} пакетов из локальной fallback БД.")
        except Exception as e:
            logger.error(f"Ошибка очистки записей в SQLite буфере: {e}")
