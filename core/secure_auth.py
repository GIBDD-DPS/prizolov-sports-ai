# ============================================
# Prizolov Sports AI - Secure Auth Bridge
# Version: 5.02 (Minor Refactor, Bugfixes & WP/Elementor Prep)
#
# CHANGELOG (5.01 → 5.02):
# - Исправлены вызовы base64.url_decode/url_encode → base64.urlsafe_b64decode/urlsafe_b64encode
# - Добавлен импорт Tuple и уточнены типы
# - Уточнён и задокументирован метод _base64url_decode
# - Лёгкая чистка форматирования без изменения бизнес-логики
# - Подготовка структуры под безопасный API-слой для WordPress Elementor
#
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production API Security & Anti-Fraud
# ============================================

import sys
import os
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

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
    """Модуль криптографической верификации JWT токенов для защиты live-панели скаута."""

    def __init__(self) -> None:
        """
        Инициализация секретного ключа и базовых параметров безопасности.
        """
        # Секретный ключ HMAC (из переменных окружения Amvera Cloud)
        self.secret_key = os.getenv(
            "PRIZOLOV_JWT_SECRET",
            "prizolov_fallback_secure_secret_key_2026_prod"
        ).encode("utf-8")

        # Время жизни токена авторизации скаута (по умолчанию 12 часов)
        self.token_ttl_seconds: int = 43200

    def _base64url_decode(self, payload: str) -> bytes:
        """
        Декодирует строку из формата Base64URL в байты.

        Args:
            payload: строка в формате base64url без/с паддинга.

        Returns:
            Декодированные байты.
        """
        rem = len(payload) % 4
        if rem > 0:
            payload += "=" * (4 - rem)
        return base64.urlsafe_b64decode(payload.encode("utf-8"))

    def verify_jwt_token(self, token: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Математически проверяет подпись HMAC-SHA256 JWT токена без тяжёлых внешних библиотек.

        Args:
            token: строка JWT (header.payload.signature).

        Returns:
            Кортеж (is_valid, token_claims_or_error).
        """
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return False, {"error": "Некорректная структура JWT"}

            header_segment, payload_segment, signature_segment = parts

            # Подготовка данных для подписи
            signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
            expected_signature = hmac.new(
                self.secret_key,
                signing_input,
                hashlib.sha256
            ).digest()

            # Кодируем ожидаемую подпись в base64url
            encoded_expected_sig = base64.urlsafe_b64encode(expected_signature).decode(
                "utf-8"
            ).replace("=", "")

            # Безопасное сравнение строк (защита от timing attacks)
            if not hmac.compare_digest(
                signature_segment.replace("=", ""),
                encoded_expected_sig
            ):
                logger.warning(
                    "[Security Alert] Зафиксирована попытка входа с поддельной JWT подписью!"
                )
                return False, {"error": "Невалидная криптографическая подпись токена"}

            # Декодирование payload
            payload_data = json.loads(
                self._base64url_decode(payload_segment).decode("utf-8")
            )

            # Проверка срока действия токена
            current_time = int(time.time())
            exp = payload_data.get("exp")
            if isinstance(exp, int) and current_time > exp:
                logger.info("[Security] Сессия авторизации скаута истекла по времени.")
                return False, {"error": "Время действия токена истекло"}

            # Проверка роли пользователя
            user_role = payload_data.get("role", "guest")
            if user_role not in ["scout", "admin"]:
                logger.warning(
                    f"[Security Access Denied] Пользователь с ролью '{user_role}' заблокирован."
                )
                return False, {
                    "error": "Недостаточно прав доступа для изменения коэффициентов"
                }

            return True, payload_data

        except Exception as e:
            logger.error(f"Ошибка парсинга и валидации JWT токена безопасности: {e}")
            return False, {"error": f"Внутренний сбой парсера: {str(e)}"}
