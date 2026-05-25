# ============================================
# Prizolov Sports AI - Local Fallback DB
# Version: 6.02 (+1.01: WAL optimization, atomic writes, corruption protection,
#                 safe fetch/clear, extended logging, WP/Elementor-ready)
#
# CHANGELOG (что сделано):
# - Добавлен PRAGMA synchronous=NORMAL для ускорения записи
# - Добавлен PRAGMA wal_autocheckpoint=2000 для стабильности
# - Добавлена защита от повреждения БД (fallback → /tmp)
# - Улучшена логика fetch (безопасный json.loads)
# - Улучшена логика clear (batch delete)
# - Добавлена атомарная запись
# - Улучшено логирование
# - Версия повышена на +1.01
#
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Data Resilience & High Availability
# ============================================

import sqlite3
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple

logger = logging.getLogger("PrizolovSportsAI.FallbackDB")


class LocalFallbackDB:
    """
    Локальный SQLite‑буфер для сохранения пакетов аналитики
    при потере связи с сетью.
    """

    def __init__(self, base_data_dir: str = "/data"):
        self.db_path = Path(base_data_dir) / "fallback_buffer.db"
        self._initialize_database()

    # ============================================================
    # INIT
    # ============================================================

    def _initialize_database(self) -> None:
        """Создаёт таблицу, включает WAL, защищает от ошибок."""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS analytics_buffer (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp_ms INTEGER NOT NULL,
                        match_id TEXT NOT NULL,
                        payload TEXT NOT NULL
                    )
                """)

                # WAL режим
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA wal_autocheckpoint=2000")

                conn.commit()

        except Exception as e:
            logger.critical(f"❌ Ошибка инициализации fallback DB: {e}. Фолбэк → /tmp")
            self.db_path = Path("/tmp/fallback_buffer.db")
            self._initialize_database()

    # ============================================================
    # BUFFER PACKAGE
    # ============================================================

    def buffer_package(self, match_id: str, package_data: Dict[str, Any]) -> bool:
        """
        Сохраняет пакет аналитики в локальный JSON‑буфер.
        """
        try:
            payload = json.dumps(package_data, ensure_ascii=False)

            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO analytics_buffer (timestamp_ms, match_id, payload) VALUES (?, ?, ?)",
                    (int(time.time() * 1000), match_id, payload)
                )
                conn.commit()

            return True

        except Exception as e:
            logger.error(f"💥 Не удалось записать пакет в fallback DB: {e}")
            return False

    # ============================================================
    # FETCH PACKAGES
    # ============================================================

    def fetch_buffered_packages(self, limit: int = 50) -> List[Tuple[int, Dict[str, Any]]]:
        """
        Возвращает [(id, payload_dict), ...] старейших пакетов.
        """
        packages = []

        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, payload FROM analytics_buffer ORDER BY id ASC LIMIT ?",
                    (limit,)
                )
                rows = cursor.fetchall()

            for row_id, payload_str in rows:
                try:
                    payload = json.loads(payload_str)
                except Exception:
                    logger.error(f"⚠️ Повреждённый JSON в fallback DB (id={row_id}). Пропускаем.")
                    continue

                packages.append((row_id, payload))

        except Exception as e:
            logger.error(f"💥 Ошибка чтения fallback DB: {e}")

        return packages

    # ============================================================
    # CLEAR PACKAGES
    # ============================================================

    def clear_buffered_packages(self, record_ids: List[int]) -> None:
        """
        Удаляет успешно отправленные пакеты.
        """
        if not record_ids:
            return

        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()

                placeholders = ",".join("?" for _ in record_ids)
                cursor.execute(
                    f"DELETE FROM analytics_buffer WHERE id IN ({placeholders})",
                    record_ids
                )

                conn.commit()

            logger.info(f"[Resilience] Очищено {len(record_ids)} пакетов из fallback DB.")

        except Exception as e:
            logger.error(f"💥 Ошибка очистки fallback DB: {e}")
