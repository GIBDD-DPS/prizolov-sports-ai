# ============================================
# Copyright (c) 2026
# Prizolov Agent OS v3.023
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

import os
import asyncio
import logging
from typing import Dict, List, Any, Optional

# Опциональный импорт Telethon (если не установлен – работаем в режиме заглушки)
try:
    from telethon import TelegramClient
    from telethon.errors import SessionPasswordNeededError
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logging.warning("Telethon не установлен, парсинг Telegram недоступен")

logger = logging.getLogger(__name__)

class TelegramParser:
    def __init__(self):
        self.api_id = os.getenv("TELEGRAM_API_ID")
        self.api_hash = os.getenv("TELEGRAM_API_HASH")
        self.phone = os.getenv("TELEGRAM_PHONE")
        self.channels = os.getenv("TELEGRAM_CHANNELS", "").split(",")
        self.client = None
        self._available = TELEGRAM_AVAILABLE and all([self.api_id, self.api_hash, self.phone])

    async def _init_client(self) -> Optional[TelegramClient]:
        if not self._available:
            return None
        if self.client is None:
            self.client = TelegramClient("prizolov_session", int(self.api_id), self.api_hash)
            await self.client.start(phone=self.phone)
        return self.client

    async def fetch_messages(self, channel: str, limit: int = 10) -> List[Dict]:
        if not self._available:
            logger.debug("Telegram недоступен (отсутствуют ключи или библиотека)")
            return []
        client = await self._init_client()
        if client is None:
            return []
        try:
            entity = await client.get_entity(channel)
            messages = []
            async for msg in client.iter_messages(entity, limit=limit):
                if msg.text and len(msg.text) > 10:
                    messages.append({
                        "channel": channel,
                        "text": msg.text,
                        "date": msg.date.isoformat(),
                        "views": getattr(msg, "views", 0),
                        "message_id": msg.id
                    })
            logger.info(f"Telegram: загружено {len(messages)} сообщений из {channel}")
            return messages
        except Exception as e:
            logger.error(f"Ошибка получения сообщений из {channel}: {e}")
            return []

    async def fetch_all(self, limit: int = 5) -> List[Dict]:
        all_messages = []
        for ch in self.channels:
            if ch.strip():
                msgs = await self.fetch_messages(ch.strip(), limit)
                all_messages.extend(msgs)
        return all_messages

    async def close(self):
        if self.client:
            await self.client.disconnect()

async def parse_telegram() -> List[Dict]:
    """Главная функция, вызываемая из планировщика."""
    parser = TelegramParser()
    try:
        messages = await parser.fetch_all()
        return messages
    finally:
        await parser.close()
