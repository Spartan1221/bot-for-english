"""Тесты сборки inline-клавиатуры копирования (bot/keyboards.py)."""

from bot.keyboards import LABEL_MEANING, LABEL_WORD, build_copy_keyboard


def test_two_buttons_in_two_rows():
    markup = build_copy_keyboard("line one", "line two")
    assert len(markup.inline_keyboard) == 2
    for row in markup.inline_keyboard:
        assert len(row) == 1


def test_copy_targets_match_lines():
    markup = build_copy_keyboard("word (example)", "перевод (definition)")
    word_button = markup.inline_keyboard[0][0]
    meaning_button = markup.inline_keyboard[1][0]

    assert word_button.copy_text.text == "word (example)"
    assert meaning_button.copy_text.text == "перевод (definition)"


def test_labels():
    markup = build_copy_keyboard("a", "b")
    assert markup.inline_keyboard[0][0].text == LABEL_WORD
    assert markup.inline_keyboard[1][0].text == LABEL_MEANING
