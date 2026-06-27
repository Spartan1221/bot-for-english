"""Конфигурация: переменные окружения, константы, тексты и настройка логирования."""

from __future__ import annotations

import logging
import os

import aiohttp
from dotenv import load_dotenv

# Загружаем .env один раз при импорте модуля.
load_dotenv()

# Токен Telegram-бота из .env.
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Общий таймаут на любой внешний API — чтобы бот не «зависал» на медленном ответе.
API_TIMEOUT = aiohttp.ClientTimeout(total=10)

# Внешние сервисы.
DICT_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
TRANSLATE_URL = "https://api.mymemory.translated.net/get"

START_TEXT = (
    "Привет! Я бот для изучения английских слов.\n\n"
    "Отправь мне английское слово или фразу — и я пришлю:\n"
    "  • пример использования;\n"
    "  • перевод на русский;\n"
    "  • определение (значение) на английском.\n\n"
    "Ответ состоит ровно из двух строк — определение, перевод и пример "
    "удобно скопировать по отдельности.\n\n"
    "Например, отправь: serendipity"
)


def setup_logging() -> None:
    """Настраивает корневой логгер. Вызывается один раз при старте бота."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
