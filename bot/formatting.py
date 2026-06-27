"""Валидация пользовательского ввода и форматирование ответа."""

from __future__ import annotations

import re

# Допустимый ввод: только латинские буквы и пробелы (одно слово или фраза).
# Это соответствует backend-словарю для английского и требованию ТЗ.
INPUT_RE = re.compile(r"^[A-Za-z]+(?:[ \t]+[A-Za-z]+)*$")


def validate_input(text: str | None) -> str | None:
    """
    Очищает и проверяет ввод. Возвращает готовый запрос или None.

    Схлопываем лишние пробелы и требуем, чтобы остались только буквы и пробелы.
    """
    if not text:
        return None
    cleaned = re.sub(r"\s+", " ", text.strip())
    return cleaned if INPUT_RE.match(cleaned) else None


def format_answer(
    word: str, example: str | None, translation: str | None, definition: str
) -> str:
    """
    Собирает ответ строго из двух строк, обычным текстом (без Markdown).

    Строка 1: слово (пример)        — без скобок, если примера нет.
    Строка 2: перевод (определение) — перевод best-effort, определение обязательное.
    """
    line1 = f"{word} ({example})" if example else word
    ru = translation if translation else "перевод недоступен"
    line2 = f"{ru} ({definition})"
    return f"{line1}\n{line2}"
