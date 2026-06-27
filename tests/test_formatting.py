"""Тесты валидации ввода и форматирования ответа (чистые функции)."""

from bot.formatting import format_answer, validate_input


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


class TestFormatAnswer:
    def test_full_answer(self):
        result = format_answer(
            "serendipity",
            "It is pure serendipity.",
            "счастливая случайность",
            "the occurrence of events by chance",
        )
        assert result == (
            "serendipity (It is pure serendipity.)\n"
            "счастливая случайность (the occurrence of events by chance)"
        )

    def test_matches_task_example(self):
        # Воспроизводит эталонный пример из task.txt.
        result = format_answer(
            "serendipity",
            "Finding a beautiful old book in a dusty attic is pure serendipity.",
            "счастливая случайность",
            "the occurrence and development of events by chance in a happy or beneficial way",
        )
        assert result == (
            "serendipity (Finding a beautiful old book in a dusty attic is pure serendipity.)\n"
            "счастливая случайность (the occurrence and development of events by chance "
            "in a happy or beneficial way)"
        )

    def test_without_example(self):
        result = format_answer("word", None, "перевод", "definition")
        assert result == "word\nперевод (definition)"

    def test_without_translation(self):
        result = format_answer("word", "example", None, "definition")
        assert result == "word (example)\nперевод недоступен (definition)"

    def test_exactly_two_lines(self):
        result = format_answer("w", "e", "t", "d")
        assert result.count("\n") == 1
