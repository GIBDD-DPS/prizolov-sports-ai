# ============================================
# Prizolov Sports AI - Setup
# Version: 4.01 (Social Sentiment & Global AI Upgrade)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production deployment at prizolov.ru
# ============================================

import asyncio
import re
import structlog
from datetime import datetime, timezone
from typing import Optional, List, Dict
from telethon import TelegramClient
from telethon.tl.types import Message

log = structlog.get_logger()

class TelegramCollector:
    """
    Асинхронный сборщик данных из Telegram-каналов и чатов.
    Использует Telethon для чтения сообщений, извлечения экспертных ставок,
    новостей и инсайдов для последующего NLP/Sentiment анализа.
    """

    def __init__(
        self,
        api_id: int,
        api_hash: str,
        session_string: Optional[str] = None,
        proxy: Optional[Dict[str, str]] = None
    ):
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_string = session_string
        self.proxy = proxy
        self.client: Optional[TelegramClient] = None

    async def __aenter__(self):
        self.client = TelegramClient(
            self.session_string or "prizolov_tg_session",
            self.api_id,
            self.api_hash,
            proxy=self.proxy
        )
        await self.client.connect()
        if not await self.client.is_user_authorized():
            raise RuntimeError("Telegram client not authorized. Provide valid api_id/hash/session.")
        log.info("Telegram client connected successfully")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.disconnect()

    async def fetch_channel_messages(self, channel_username: str, limit: int = 50) -> List[Dict]:
        """Получение последних сообщений из указанного канала/чата"""
        if not self.client:
            log.error("Telegram client not initialized")
            return []

        messages_data = []
        try:
            async for message in self.client.iter_messages(channel_username, limit=limit):
                parsed = self._parse_message(message)
                if parsed:
                    messages_data.append(parsed)
            log.info("Fetched Telegram messages", channel=channel_username, count=len(messages_data))
        except Exception as e:
            log.error("Failed to fetch Telegram messages", channel=channel_username, error=str(e))

        return messages_data

    def _parse_message(self, message: Message) -> Optional[Dict]:
        """Извлечение и очистка данных из сообщения"""
        if not message.text:
            return None

        # Базовая очистка: удаление markdown-ссылок, анонимизация URL
        clean_text = re.sub(r'!\[.*?\]\(.*?\)', '', message.text)
        clean_text = re.sub(r'https?://\S+|www\.\S+', '[LINK]', clean_text)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()

        if not clean_text or len(clean_text) < 10:
            return None

        return {
            "source": "telegram",
            "channel_id": str(message.chat_id) if message.chat else None,
            "channel_username": message.chat.username if message.chat else None,
            "message_id": message.id,
            "text": clean_text,
            "raw_text": message.text,
            "timestamp": message.date.isoformat() if message.date else datetime.now(timezone.utc).isoformat(),
            "has_media": bool(message.media),
            "fetched_at": datetime.now(timezone.utc).isoformat()
        }

    async def collect_from_channels(self, channels: List[str], limit_per_channel: int = 50) -> List[Dict]:
        """Пакетный сбор сообщений из списка каналов (последовательно для соблюдения лимитов TG)"""
        all_messages = []
        for channel in channels:
            try:
                msgs = await self.fetch_channel_messages(channel, limit_per_channel)
                all_messages.extend(msgs)
                # Небольшая задержка между каналами для избежания floodwait
                await asyncio.sleep(1.5)
            except Exception as e:
                log.error("Channel collection error", channel=channel, error=str(e))

        log.info("Telegram collection batch completed", total=len(all_messages))
        return all_messages
