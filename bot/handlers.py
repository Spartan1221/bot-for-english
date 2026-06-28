"""Хэндлеры aiogram и регистрация обработчиков на диспетчере."""

from __future__ import annotations

import asyncio
import logging

import aiohttp
from aiogram import Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message

from .api import (
    fetch_free_definition,
    fetch_microsoft_translate,
    fetch_yandex_dictionary,
)
from .config import START_TEXT
from .formatting import build_sections, classify_input, sections_to_text, validate_input
from .keyboards import build_copy_keyboard

log = logging.getLogger(__name__)


async def cmd_start(message: Message) -> None:
    """Команда /start — приветствие и краткая инструкция."""
    await message.answer(START_TEXT)


async def handle_word(
    message: Message, http_session: aiohttp.ClientSession
) -> None:
    """Основная логика: проверка ввода → запросы к API → сборка секций → ответ."""
    # http_session приходит через dependency injection из dp["http_session"].

    # 1. Валидация ввода.
    query = validate_input(message.text)
    if query is None:
        await message.answer(
            "Пожалуйста, отправьте английское слово или фразу "
            "(только буквы и пробелы)."
        )
        return

    # 2. Классификация: отдельное слово (возможно, с артиклем a/an/the/to) или фраза.
    #    Артикль задаёт нужную часть речи: a/an/the — noun, to — verb, без артикля — обе.
    head, allowed_pos, is_phrase = classify_input(query)

    # 3. Запросы к API. Все вызовы best-effort: возвращают None/пусто при сбое.
    if is_phrase:
        # Фразы нет в словаре — только машинный перевод, без примера и определения.
        translation = await fetch_microsoft_translate(http_session, head)
        example = None
        definition = None
    else:
        # Отдельное слово: параллельно — Free Dictionary (определение + пример)
        # и Yandex Dictionary (переводы нужных частей речи).
        api_query = head.lower()
        (definition, example), variants = await asyncio.gather(
            fetch_free_definition(http_session, api_query),
            fetch_yandex_dictionary(http_session, api_query, allowed_pos),
        )
        translation = ", ".join(variants) if variants else None
        # Слова нет в словаре — пробуем машинный перевод как фолбэк.
        if translation is None:
            translation = await fetch_microsoft_translate(http_session, api_query)

    # 4. Если перевода нет совсем — сообщаем, что перевести не удалось.
    if not translation:
        await message.answer(f"Не удалось перевести «{query}». 😕")
        return

    # 5. Сборка секций, текст (с разделителем) и клавиатура копирования.
    sections = build_sections(head, example, translation, definition, is_phrase)
    await message.answer(
        sections_to_text(sections),
        reply_markup=build_copy_keyboard(sections),
    )


def register_handlers(dp: Dispatcher) -> None:
    """Регистрирует все хэндлеры на диспетчере. Порядок важен: /start раньше catch-all."""
    dp.message.register(cmd_start, CommandStart())
    dp.message.register(handle_word)
