"""Валидация пользовательского ввода и сборка ответа по секциям."""

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


def build_sections(
    word: str,
    example: str | None,
    translation: str | None,
    definition: str | None,
    is_phrase: bool,
) -> list[tuple[str, str]]:
    """
    Собирает ответ из секций (kind, text) в порядке вывода.

    Слово:   слово+пример, перевод, значение.
    Фраза:   фраза, перевод (значения и примера у фразы нет).

    Отсутствующие части (нет примера/перевода/определения) в список не попадают —
    ответ и набор кнопок адаптируются под то, что реально пришло из API.
    """
    sections: list[tuple[str, str]] = []

    if is_phrase:
        sections.append(("phrase", word))
    else:
        line1 = f"{word} ({example})" if example else word
        sections.append(("word", line1))

    if translation:
        sections.append(("translation", translation))

    if not is_phrase and definition:
        sections.append(("definition", definition))

    return sections


def sections_to_text(sections: list[tuple[str, str]]) -> str:
    """Склеивает тексты секций в сообщение (обычный текст, без Markdown)."""
    return "\n".join(text for _, text in sections)
