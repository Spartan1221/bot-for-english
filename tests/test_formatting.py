"""Тесты валидации, обработки артиклей и сборки ответа-таблицы (чистые функции)."""

from bot.formatting import (
    build_sections,
    sections_to_table,
    strip_leading_article,
    validate_input,
)


class TestValidateInput:
    def test_single_word(self):
        assert validate_input("serendipity") == "serendipity"

    def test_phrase(self):
        assert validate_input("new york") == "new york"

    def test_preserves_case(self):
        assert validate_input("Serendipity") == "Serendipity"

    def test_collapses_whitespace(self):
        assert validate_input("  hello   world  ") == "hello world"

    def test_empty_string(self):
        assert validate_input("") is None

    def test_none(self):
        assert validate_input(None) is None

    def test_digits_rejected(self):
        assert validate_input("hello123") is None

    def test_punctuation_rejected(self):
        assert validate_input("hello!") is None

    def test_apostrophe_rejected(self):
        # По ТЗ допускаются только буквы и пробелы.
        assert validate_input("don't") is None

    def test_cyrillic_rejected(self):
        assert validate_input("привет") is None

    def test_only_spaces(self):
        assert validate_input("    ") is None


class TestStripLeadingArticle:
    def test_strips_to(self):
        assert strip_leading_article("to go") == "go"

    def test_strips_a_an(self):
        assert strip_leading_article("a book") == "book"
        assert strip_leading_article("an apple") == "apple"

    def test_case_insensitive_particle(self):
        assert strip_leading_article("TO GO") == "GO"

    def test_strips_only_first_token(self):
        # 'to be or not to be' -> убираем только ведущее 'to'.
        assert strip_leading_article("to be or not to be") == "be or not to be"

    def test_no_article_unchanged(self):
        assert strip_leading_article("good morning") == "good morning"

    def test_single_particle_unchanged(self):
        # Одиночный артикль/частицу не отбрасываем — иначе нечего искать.
        assert strip_leading_article("to") == "to"
        assert strip_leading_article("a") == "a"


class TestBuildSections:
    def test_word_full(self):
        sections = build_sections("set", "a set of tools", "набор, множество", "a group of things", False)
        assert sections == [
            ("word", "set (a set of tools)"),
            ("translation", "набор, множество"),
            ("definition", "a group of things"),
        ]

    def test_word_without_example(self):
        sections = build_sections("set", None, "набор", "def", False)
        assert sections[0] == ("word", "set")

    def test_word_without_definition(self):
        sections = build_sections("set", "ex", "набор", None, False)
        kinds = [k for k, _ in sections]
        assert "definition" not in kinds

    def test_phrase(self):
        sections = build_sections("good morning", None, "доброе утро", None, True)
        assert sections == [
            ("phrase", "good morning"),
            ("translation", "доброе утро"),
        ]

    def test_phrase_ignores_definition_and_example(self):
        sections = build_sections("good morning", "ex", "доброе утро", "def", True)
        assert [k for k, _ in sections] == ["phrase", "translation"]


class TestSectionsToTable:
    def test_simple_exact(self):
        # Один раздел — таблица с заголовком и разделителем из '-'.
        table = sections_to_table([("word", "go")])
        assert table == (
            "| Часть | Содержимое |\n"
            "|-------|------------|\n"
            "| Слово | go         |"
        )

    def test_contains_all_values(self):
        sections = [
            ("word", "set (a set of tools)"),
            ("translation", "набор, множество"),
            ("definition", "a group of things"),
        ]
        table = sections_to_table(sections)
        for value in ("set (a set of tools)", "набор, множество", "a group of things"):
            assert value in table
        # Структура: есть и '|', и строка-разделитель из '-'.
        assert "|" in table
        assert any(set(line.replace("|", "")) == {"-"} for line in table.split("\n"))

    def test_empty(self):
        assert sections_to_table([]) == ""
