"""Inline-клавиатуры для ответов бота."""

from __future__ import annotations

from aiogram.types import (
    CopyTextButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

# Подписи кнопок. Каждая кнопка лежит в отдельной строке — так длинные подписи
# не обрезаются и обе кнопки всегда видны целиком.
LABEL_WORD = "📋 Слово + пример"
LABEL_MEANING = "📋 Значение + перевод"


def build_copy_keyboard(line1: str, line2: str) -> InlineKeyboardMarkup:
    """
    Клавиатура из двух кнопок под ответом.

    Каждая кнопка — это CopyTextButton: тап копирует текст напрямую в буфер
    обмена пользователя, без callback-запроса к боту. Кнопка 1 копирует первую
    строку ответа (слово с примером), кнопка 2 — вторую (перевод с определением).
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=LABEL_WORD, copy_text=CopyTextButton(text=line1))],
            [InlineKeyboardButton(text=LABEL_MEANING, copy_text=CopyTextButton(text=line2))],
        ]
    )
