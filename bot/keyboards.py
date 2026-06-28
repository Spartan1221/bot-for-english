"""Inline-клавиатуры для ответов бота."""

from __future__ import annotations

from aiogram.types import (
    CopyTextButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

# Подписи кнопок по типу секции. Каждая кнопка лежит в отдельной строке — так длинные
# подписи не обрезаются и все кнопки всегда видны целиком.
SECTION_LABELS = {
    "word": "📋 Слово + пример",
    "phrase": "📋 Фраза",
    "translation": "📋 Перевод",
    "definition": "📋 Значение",
}


def build_copy_keyboard(sections: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    """
    Клавиатура копирования по секциям ответа.

    Каждая секция (kind, text) → своя кнопка CopyTextButton: тап копирует текст секции
    напрямую в буфер обмена пользователя, без callback-запроса к боту. Кнопки идут в том
    же порядке, что и строки ответа.
    """
    rows = []
    for kind, text in sections:
        label = SECTION_LABELS.get(kind, kind.capitalize())
        rows.append(
            [InlineKeyboardButton(text=label, copy_text=CopyTextButton(text=text))]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)
