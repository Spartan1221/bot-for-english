"""Сборка и запуск бота."""

from __future__ import annotations

import logging
import sys

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from .config import (
    API_TIMEOUT,
    BOT_TOKEN,
    YANDEX_CLOUD_API_KEY,
    YANDEX_DICT_API_KEY,
    YANDEX_FOLDER_ID,
    setup_logging,
)
from .handlers import register_handlers

log = logging.getLogger(__name__)


async def main() -> None:
    """Точка входа: создаёт бота, диспетчер, общий HTTP-сеанс и запускает polling."""
    setup_logging()

    # Проверяем обязательные секреты: токен бота, ключи Yandex Cloud Translate и Yandex Dictionary.
    missing = [
        name
        for name, value in (
            ("BOT_TOKEN", BOT_TOKEN),
            ("YANDEX_CLOUD_API_KEY", YANDEX_CLOUD_API_KEY),
            ("YANDEX_FOLDER_ID", YANDEX_FOLDER_ID),
            ("YANDEX_DICT_API_KEY", YANDEX_DICT_API_KEY),
        )
        if not value
    ]
    if missing:
        log.error(
            "Не заданы обязательные переменные: %s. Укажите их в файле .env (см. DEPLOYMENT.md).",
            ", ".join(missing),
        )
        sys.exit(1)

    # parse_mode не задаём намеренно: нужен обычный текст без Markdown.
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties())
    dp = Dispatcher()
    register_handlers(dp)

    # Один общий HTTP-сеанс на всё время работы бота — переиспользует соединения.
    # Через dp[...] сессия становится доступна хэндлерам как параметр http_session.
    http_session = aiohttp.ClientSession(timeout=API_TIMEOUT)
    dp["http_session"] = http_session

    log.info("Бот запускается...")
    try:
        await dp.start_polling(bot)
    finally:
        await http_session.close()
        await bot.session.close()
