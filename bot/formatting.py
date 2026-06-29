"""Валидация ввода, определение части речи по артиклю и сборка ответа."""

from __future__ import annotations

import re

# Допустимый ввод: только латинские буквы и пробелы (одно слово или фраза).
INPUT_RE = re.compile(r"^[A-Za-z]+(?:[ \t]+[A-Za-z]+)*$")

# Ведущий артикль/частица → какая часть речи нужна в переводе.
# a/an/the указывают на существительное, to — на глагол.
ARTICLE_POS = {"a": "noun", "an": "noun", "the": "noun", "to": "verb"}

# Разделитель между строками ответа.
SECTION_SEPARATOR = "-----"


def validate_input(text: str | None) -> str | None:
    """
    Очищает и проверяет ввод. Возвращает готовый запрос или None.

    Схлопываем лишние пробелы и требуем, чтобы остались только буквы и пробелы.
    """
    if not text:
        return None
    cleaned = re.sub(r"\s+", " ", text.strip())
    return cleaned if INPUT_RE.match(cleaned) else None


def classify_input(query: str) -> tuple[str, list[str] | None, bool]:
    """
    Определяет, что искать — отдельное слово (с фильтром по части речи) или фразу.

    Возвращает (голова, allowed_pos, is_phrase):
    - `'<article> <word>'`: a/an/the → слово, только noun; to → слово, только verb.
    - одиночное слово без артикля → слово, allowed_pos = None (все части речи: noun,
      verb, прилагательное и т.д. — чтобы прилагательные получали несколько переводов).
    - иначе (2+ слова без ведущего артикля / предложение) → фраза, allowed_pos = [].
    """
    tokens = query.split()
    if len(tokens) == 1:
        return tokens[0], None, False
    if len(tokens) == 2 and tokens[0].lower() in ARTICLE_POS:
        return tokens[1], [ARTICLE_POS[tokens[0].lower()]], False
    return query, [], True


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
    """
    Склеивает тексты секций, разделяя их строкой '-----'.

    Обычный текст без Markdown (parse_mode выключен) — разделитель рисуется буквально.
    Кнопки копирования (build_copy_keyboard) копируют значения секций как есть.
    """
    if not sections:
        return ""
    return f"\n{SECTION_SEPARATOR}\n".join(text for _, text in sections)
