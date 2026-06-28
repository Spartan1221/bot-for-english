"""Тесты валидации, классификации артиклей/частей речи и сборки ответа (чистые функции)."""

from bot.formatting import (
    build_sections,
    classify_input,
    sections_to_text,
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
        assert validate_input("don't") is None

    def test_cyrillic_rejected(self):
        assert validate_input("привет") is None

    def test_only_spaces(self):
        assert validate_input("    ") is None


class TestClassifyInput:
    def test_single_word_both_pos(self):
        assert classify_input("set") == ("set", ["noun", "verb"], False)

    def test_article_noun(self):
        assert classify_input("a book") == ("book", ["noun"], False)
        assert classify_input("an apple") == ("apple", ["noun"], False)
        assert classify_input("the set") == ("set", ["noun"], False)

    def test_article_verb(self):
        assert classify_input("to go") == ("go", ["verb"], False)

    def test_case_insensitive_article(self):
        assert classify_input("A Book") == ("Book", ["noun"], False)
        assert classify_input("TO GO") == ("GO", ["verb"], False)

    def test_single_article_treated_as_word(self):
        # Одиночный артикль — это слово, классифицируется как «и noun, и verb».
        assert classify_input("to") == ("to", ["noun", "verb"], False)

    def test_phrase(self):
        assert classify_input("good morning") == ("good morning", [], True)

    def test_sentence(self):
        assert classify_input("i love you") == ("i love you", [], True)

    def test_article_plus_many_words_is_phrase(self):
        # 'to go home' — это предложение, не «to + слово».
        assert classify_input("to go home") == ("to go home", [], True)


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
        assert "definition" not in [k for k, _ in sections]

    def test_phrase(self):
        sections = build_sections("good morning", None, "доброе утро", None, True)
        assert sections == [("phrase", "good morning"), ("translation", "доброе утро")]


class TestSectionsToText:
    def test_joins_with_separator(self):
        sections = [("word", "set (a set of tools)"), ("translation", "набор"), ("definition", "def")]
        assert sections_to_text(sections) == (
            "set (a set of tools)\n-----\nнабор\n-----\ndef"
        )

    def test_single_section_no_separator(self):
        assert sections_to_text([("phrase", "good morning")]) == "good morning"

    def test_empty(self):
        assert sections_to_text([]) == ""
