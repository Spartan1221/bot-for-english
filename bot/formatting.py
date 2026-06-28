"""Валидация пользовательского ввода и сборка ответа (секции + таблица)."""

from __future__ import annotations

import re

# Допустимый ввод: только латинские буквы и пробелы (одно слово или фраза).
# Это соответствует backend-словарю для английского и требованию ТЗ.
INPUT_RE = re.compile(r"^[A-Za-z]+(?:[ \t]+[A-Za-z]+)*$")

# Ведущие служебные слова, которые отбрасываем перед словарным lookup:
# артикли (a, an) и инфинитивная частица (to).
LEADING_PARTICLES = ("a", "an", "to")

# Подписи строк таблицы по типу секции.
TABLE_LABELS = {
    "word": "Слово",
    "phrase": "Фраза",
    "translation": "Перевод",
    "definition": "Значение",
}


def validate_input(text: str | None) -> str | None:
    """
    Очищает и проверяет ввод. Возвращает готовый запрос или None.

    Схлопываем лишние пробелы и требуем, чтобы остались только буквы и пробелы.
    """
    if not text:
        return None
    cleaned = re.sub(r"\s+", " ", text.strip())
    return cleaned if INPUT_RE.match(cleaned) else None


def strip_leading_article(query: str) -> str:
    """
    Отбрасывает ведущий артикль/частицу (a/an/to), если за ним есть ещё текст.

    'to go' -> 'go', 'a book' -> 'book', 'an apple' -> 'apple'.
    Одиночный артикль ('a', 'to') и фразы без артикля ('good morning') не меняет.
    Устойчива к любым пробельным разделителям (split() без аргумента) — хотя на вход
    обычно поступает уже нормализованный запрос из validate_input.
    """
    parts = query.split()
    if len(parts) >= 2 and parts[0].lower() in LEADING_PARTICLES:
        return " ".join(parts[1:])
    return query


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


def sections_to_table(sections: list[tuple[str, str]]) -> str:
    """
    Превращает секции в обычнотекстовую таблицу (заголовок + разделитель из «-»,
    колонки разделены «|»). parse_mode не включаем, поэтому символы рисуются как есть.

    Кнопки копирования (build_copy_keyboard) копируют значения правой колонки как есть.
    """
    if not sections:
        return ""

    rows = [("Часть", "Содержимое")]
    rows += [(TABLE_LABELS.get(kind, kind.capitalize()), text) for kind, text in sections]

    w_label = max(len(label) for label, _ in rows)
    w_value = max(len(value) for _, value in rows)

    def row(label: str, value: str) -> str:
        return f"| {label.ljust(w_label)} | {value.ljust(w_value)} |"

    separator = f"|{'-' * (w_label + 2)}|{'-' * (w_value + 2)}|"
    lines = [row(*rows[0]), separator]
    lines += [row(label, value) for label, value in rows[1:]]
    return "\n".join(lines)
