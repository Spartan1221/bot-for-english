"""Тесты валидации ввода и форматирования ответа (чистые функции)."""

from bot.formatting import format_answer, format_answer_parts, validate_input


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


class TestFormatAnswerParts:
    def test_returns_two_parts(self):
        line1, line2 = format_answer_parts("word", "ex", "перевод", "def")
        assert line1 == "word (ex)"
        assert line2 == "перевод (def)"

    def test_consistent_with_format_answer(self):
        # join частей должен совпадать с готовым ответом — для разных наборов данных.
        cases = [
            ("serendipity", "It is pure serendipity.", "счастливая случайность", "def"),
            ("word", None, "перевод", "definition"),
            ("word", "example", None, "definition"),
            ("w", "e", "t", "d"),
        ]
        for word, example, translation, definition in cases:
            line1, line2 = format_answer_parts(word, example, translation, definition)
            assert f"{line1}\n{line2}" == format_answer(word, example, translation, definition)

    def test_without_example(self):
        line1, line2 = format_answer_parts("word", None, "перевод", "definition")
        assert line1 == "word"
        assert line2 == "перевод (definition)"

    def test_without_translation(self):
        line1, line2 = format_answer_parts("word", "example", None, "definition")
        assert line2 == "перевод недоступен (definition)"
