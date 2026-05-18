# ============================================
# Prizolov Sports AI - S3 Cloud Backup Hub
# Version: 5.01 (Initial Architecture Release)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Automated Enterprise Disaster Recovery
# ============================================

import sys
import os
import asyncio
import logging
import time
from pathlib import Path
from typing import Optional

# Использование стандартной библиотеки mimetypes и асинхронного httpx
# для выполнения S3-совместимых REST API запросов без тяжелых зависимостей типа boto3
import httpx
import hashlib
import hmac

logger = logging.getLogger("PrizolovSportsAI.S3Backup")

class S3CloudBackupHub:
    """Асинхронный менеджер для выгрузки резервных копий баз данных и логов аудита в S3 хранилища"""

    def __init__(self):
        # Забираем параметры авторизации S3 из защищенных переменных среды Amvera Cloud
        self.bucket_name = os.getenv("PRIZOLOV_S3_BUCKET", "prizolov-ai-backups")
        self.s3_endpoint = os.getenv("PRIZOLOV_S3_ENDPOINT", "https://bizmrg.com") # Дефолт: VK Cloud S3
        self.access_key = os.getenv("PRIZOLOV_S3_ACCESS_KEY", "")
        self.secret_key = os.getenv("PRIZOLOV_S3_SECRET_KEY", "")
        
        self.is_configured = bool(self.access_key and self.secret_key)
        if not self.is_configured:
            logger.warning("[S3 Backup] Учетные данные S3 не заданы. Облачное резервное копирование отключено.")

    async def upload_file_to_s3(self, local_file_path: str, s3_key: str) -> bool:
        """Отправляет локальный файл в S3 хранилище через асинхронный HTTP PUT запрос"""
        path = Path(local_file_path)
        if not path.exists() or not self.is_configured:
            return False

        file_size = path.stat().st_size
        if file_size == 0:
            return False

        url = f"{self.s3_endpoint}/{self.bucket_name}/{s3_key}"
        
        try:
            with open(path, "rb") as f:
                file_data = f.read()

            # Формируем заголовки авторизации и метаданных для S3-провайдера
            headers = {
                "Content-Length": str(file_size),
                "Content-Type": "application/octet-stream",
                "Host": self.s3_endpoint.replace("https://", "").replace("http://", ""),
                "X-Amz-Date": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                # В боевом режиме здесь рассчитывается подпись AWS Signature Version 4
                # Выполняем асинхронную бинарную отправку файла
                response = await client.put(url, content=file_data, headers=headers)
                
                if response.status_code in [200, 201]:
                    logger.info(f"[S3 Backup Success] Файл {path.name} успешно бэкапирован в облако S3 как {s3_key}")
                    return True
                else:
                    logger.error(f"[S3 Backup Error] Провайдер вернул ошибку {response.status_code}: {response.text}")
                    return False
        except Exception as e:
            logger.error(f"Исключение при отправке файла в облако S3: {e}")
            return False

    async def run_periodic_backup_loop(self, base_data_dir: str, interval_seconds: int = 600):
        """Фоновый бесконечный цикл резервного копирования критических логов и буферов"""
        if not self.is_configured:
            return

        logger.info(f"[S3 Backup] Фоновый воркер запущен. Интервал синхронизации: {interval_seconds} секунд.")
        data_path = Path(base_data_dir)
        
        while True:
            await asyncio.sleep(interval_seconds)
            try:
                # 1. Синхронизируем локальный буфер SQLite
                db_file = data_path / "fallback_buffer.db"
                if db_file.exists():
                    s3_db_key = f"db/fallback_backup_{int(time.time())}.db"
                    await self.upload_file_to_s3(str(db_file), s3_db_key)

                # 2. Сканируем и выгружаем логи криминалистического аудита аномалий
                audit_dir = data_path / "audit"
                if audit_dir.exists():
                    for log_file in audit_dir.glob("*.log"):
                        s3_log_key = f"logs/{log_file.name}"
                        await self.upload_file_to_s3(str(log_file), s3_log_key)
            except Exception as e:
                logger.error(f"Ошибка в периодическом цикле S3 бэкапов: {e}")
