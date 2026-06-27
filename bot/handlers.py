"""Хэндлеры aiogram и регистрация обработчиков на диспетчере."""

from __future__ import annotations

import asyncio
import logging

import aiohttp
from aiogram import Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message

from .api import WordNotFound, fetch_definition, fetch_translation
from .config import START_TEXT
from .formatting import format_answer, validate_input

log = logging.getLogger(__name__)


async def cmd_start(message: Message) -> None:
    """Команда /start — приветствие и краткая инструкция."""
    await message.answer(START_TEXT)


async def handle_word(
    message: Message, http_session: aiohttp.ClientSession
) -> None:
    """Основная логика: проверка ввода → запросы к API → форматирование → ответ."""
    # http_session приходит через dependency injection из dp["http_session"].

    # 1. Валидация ввода.
    query = validate_input(message.text)
    if query is None:
        await message.answer(
            "Пожалуйста, отправьте английское слово или фразу "
            "(только буквы и пробелы)."
        )
        return

    api_query = query.lower()  # Dictionary API регистронезависим, но нормализуем.

    # 2. Параллельные запросы к обоим API.
    try:
        (definition, example), translation = await asyncio.gather(
            fetch_definition(http_session, api_query),
            fetch_translation(http_session, api_query),
        )
    except WordNotFound:
        await message.answer(f"Не удалось найти «{query}» в словаре. 😕")
        return
    except asyncio.TimeoutError:
        await message.answer("Сервисы не ответили вовремя. Попробуйте ещё раз. ⏳")
        return
    except aiohttp.ClientError:
        await message.answer("Ошибка сети. Проверьте подключение и попробуйте снова.")
        return

    # 3. Форматирование и отправка.
    await message.answer(format_answer(query, example, translation, definition))


def register_handlers(dp: Dispatcher) -> None:
    """Регистрирует все хэндлеры на диспетчере. Порядок важен: /start раньше catch-all."""
    dp.message.register(cmd_start, CommandStart())
    dp.message.register(handle_word)
