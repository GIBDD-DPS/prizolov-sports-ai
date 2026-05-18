# ============================================
# Prizolov Sports AI - gRPC-Web Proxy Connector
# Version: 5.01 (Initial Architecture Release)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: High-Performance Direct Browser Streaming
# ============================================

import sys
import os
import base64
import struct
from pathlib import Path
from typing import Dict, Any, Optional

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import logging
logger = logging.getLogger("PrizolovSportsAI.gRPCWebProxy")

class gRPCWebProxyConnector:
    """Транспортный прокси-модуль для упаковки Protobuf-сообщений в браузерный формат gRPC-Web"""

    def __init__(self):
        pass

    def encode_grpc_web_frame(self, protobuf_message: Any, is_trailer: bool = False) -> bytes:
        """
        Упаковывает скомпилированное Protobuf сообщение в валидный бинарный фрейм gRPC-Web.
        Структура фрейма:
        - 1 байт: Флаги (0x00 - данные, 0x80 - трейлеры/заголовки окончания)
        - 4 байта: Длина сообщения в Big-Endian (сетевой порядок байт)
        - N байт: Сериализованное Protobuf тело
        """
        try:
            # Сериализуем Protobuf-объект в сырые байты
            serialized_data = protobuf_message.SerializeToString()
            msg_len = len(serialized_data)
            
            # Установка флага типа фрейма
            flag = 0x80 if is_trailer else 0x00
            
            # Упаковываем заголовок: 1 байт (B) + 4 байта unsigned int (I) в Big-Endian (>)
            header = struct.pack(">BI", flag, msg_len)
            
            return header + serialized_data
        except Exception as e:
            logger.error(f"Ошибка кодирования gRPC-Web фрейма: {e}")
            return b""

    def encode_base64_stream(self, grpc_web_bytes: bytes) -> str:
        """
        Преобразует бинарный gRPC-Web фрейм в текстовую Base64-строку.
        Этот формат используется, если браузерный клиент старой версии не поддерживает потоковый binary-mode.
        """
        if not grpc_web_bytes:
            return ""
        return base64.b64encode(grpc_web_bytes).decode('utf-8')

    def parse_browser_grpc_web_request(self, raw_body: bytes) -> Optional[bytes]:
        """
        Распаковывает входящий gRPC-Web запрос от JavaScript-клиента фронтенда.
        Убирает 5-байтовый веб-заголовок и извлекает чистый Protobuf-слой для отправки в Agent OS.
        """
        try:
            if len(raw_body) < 5:
                return None
                
            # Извлекаем длину сообщения из заголовка (байты с 1 по 5)
            _, msg_len = struct.unpack(">BI", raw_body[:5])
            
            # Срез чистого Protobuf-тела
            protobuf_payload = raw_body[5:5 + msg_len]
            return protobuf_payload
        except Exception as e:
            logger.error(f"Ошибка парсинга gRPC-Web запроса браузера: {e}")
            return None
