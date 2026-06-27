"""Тесты валидации ввода и сборки ответа по секциям (чистые функции)."""

from bot.formatting import build_sections, sections_to_text, validate_input


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
        # У фразы не бывает значения и примера — даже если что-то пришло.
        sections = build_sections("good morning", "ex", "доброе утро", "def", True)
        kinds = [k for k, _ in sections]
        assert kinds == ["phrase", "translation"]

    def test_word_without_translation(self):
        sections = build_sections("set", "ex", None, "def", False)
        kinds = [k for k, _ in sections]
        assert "translation" not in kinds
        assert kinds == ["word", "definition"]


class TestSectionsToText:
    def test_joins_with_newline(self):
        sections = [("word", "set (ex)"), ("translation", "набор"), ("definition", "def")]
        assert sections_to_text(sections) == "set (ex)\nнабор\ndef"

    def test_empty(self):
        assert sections_to_text([]) == ""

    def test_matches_build_sections_order(self):
        sections = build_sections("set", "a set of tools", "набор, множество", "a group of things", False)
        text = sections_to_text(sections)
        assert text == "set (a set of tools)\nнабор, множество\na group of things"
