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

# Microsoft (Azure) Translator: ключ и регион ресурса. Нужны для перевода слов и фраз.
AZURE_TRANSLATOR_KEY = os.getenv("AZURE_TRANSLATOR_KEY")
AZURE_TRANSLATOR_REGION = os.getenv("AZURE_TRANSLATOR_REGION")

# Классический Yandex Dictionary: отдельный API-ключ. Нужен для переводов по частям
# речи для отдельных слов.
YANDEX_DICT_API_KEY = os.getenv("YANDEX_DICT_API_KEY")

# Общий таймаут на любой внешний API — чтобы бот не «зависал» на медленном ответе.
API_TIMEOUT = aiohttp.ClientTimeout(total=10)

# Внешние сервисы.
# Перевод (слова и предложения) — Microsoft (Azure) Translator.
AZURE_TRANSLATE_URL = (
    "https://api.cognitive.microsofttranslator.com/translate?api-version=3.0&from=en&to=ru"
)
# Переводы по частям речи для отдельных слов — Yandex Dictionary.
YANDEX_DICT_URL = "https://dictionary.yandex.net/api/v1/dicservice.json/lookup"
# Английское определение (значение) + пример — Free Dictionary API.
DICT_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/{word}"

START_TEXT = (
    "Привет! Я бот для изучения английских слов.\n\n"
    "Отправь мне английское слово или фразу — и я пришлю:\n"
    "  • перевод на русский;\n"
    "  • определение (значение) на английском;\n"
    "  • и, если найдётся, — пример использования.\n\n"
    "Для слова можно указать часть речи артиклем: a/an/the — существительное, "
    "to — глагол (без артикля — и существительное, и глагол).\n\n"
    "Под ответом появятся кнопки — каждая копирует свою часть. Фразы переводятся, "
    "но без определения и примера.\n\n"
    "Например, отправь: serendipity"
)


def setup_logging() -> None:
    """Настраивает корневой логгер. Вызывается один раз при старте бота."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
