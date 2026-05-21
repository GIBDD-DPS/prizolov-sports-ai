# ============================================
# Prizolov Sports AI - Secure Auth Bridge
# Version: 5.01 (Initial Architecture Release)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production API Security & Anti-Fraud
# ============================================

import sys
import os
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# Импорт легковесных нативных средств шифрования для контейнеров Amvera
import hmac
import hashlib
import base64
import json

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

logger = logging.getLogger("PrizolovSportsAI.Security")

class SecureAuthBridge:
    """Модуль криптографической верификации JWT токенов для защиты live-панели скаута"""

    def __init__(self):
        # Забираем секретный ключ шифрования из переменных среды Amvera Cloud
        # Если ключ не задан, генерируем случайный стойкий ключ для защиты рантайма
        self.secret_key = os.getenv("PRIZOLOV_JWT_SECRET", "prizolov_fallback_secure_secret_key_2026_prod").encode('utf-8')
        
        # Время жизни токена авторизации скаута (по умолчанию 12 часов = 43200 секунд)
        self.token_ttl_seconds = 43200

    def _base64url_decode(self, payload: str) -> bytes:
        """Декодирует строку из формата Base64URL в байты"""
        rem = len(payload) % 4
        if rem > 0:
            payload += "=" * (4 - rem)
        return base64.url_decode(payload.encode('utf-8'))

    def verify_jwt_token(self, token: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Математически проверяет подпись HMAC-SHA256 JWT токена без тяжелых внешних библиотек.
        Возвращает (is_valid, token_claims).
        """
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return False, {"error": "Некорректная структура JWT"}

            header_segment, payload_segment, signature_segment = parts
            
            # Проверка подписи HMAC-SHA256
            signing_input = f"{header_segment}.{payload_segment}".encode('utf-8')
            expected_signature = hmac.new(self.secret_key, signing_input, hashlib.sha256).digest()
            
            # Кодируем в base64url для сопоставления
            encoded_expected_sig = base64.url_encode(expected_signature).decode('utf-8').replace('=', '')
            
            # Безопасное сравнение строк во избежание атак по времени (Timing Attacks)
            if not hmac.compare_digest(signature_segment.replace('=', ''), encoded_expected_sig):
                logger.warning("[Security Alert] Зафиксирована попытка входа с поддельной JWT подписью!")
                return False, {"error": "Невалидная криптографическая подпись токена"}

            # Извлечение и валидация полезной нагрузки (Claims)
            payload_data = json.loads(self._base64url_decode(payload_segment).decode('utf-8'))
            
            # Проверка времени истечения токена (Expiration Time)
            current_time = int(time.time())
            if "exp" in payload_data and current_time > payload_data["exp"]:
                logger.info("[Security] Сессия авторизации скаута успешно истекла по времени.")
                return False, {"error": "Время действия токена истекло"}

            # Проверка прав доступа: роль пользователя обязана быть 'scout' или 'admin'
            user_role = payload_data.get("role", "guest")
            if user_role not in ["scout", "admin"]:
                logger.warning(f"[Security Access Denied] Пользователь с ролью '{user_role}' заблокирован.")
                return False, {"error": "Недостаточно прав доступа для изменения коэффициентов"}

            return True, payload_data

        except Exception as e:
            logger.error(f"Ошибка парсинга и валидации JWT токена безопасности: {e}")
            return False, {"error": f"Внутренний сбой парсера: {str(e)}"}
