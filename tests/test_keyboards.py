"""Тесты сборки inline-клавиатуры копирования (bot/keyboards.py)."""

from bot.keyboards import SECTION_LABELS, build_copy_keyboard


def test_one_button_per_section_in_order():
    sections = [
        ("word", "set (a set of tools)"),
        ("translation", "набор, множество"),
        ("definition", "a group of things"),
    ]
    markup = build_copy_keyboard(sections)

    assert len(markup.inline_keyboard) == 3
    for row in markup.inline_keyboard:
        assert len(row) == 1

    # Подписи и цели копирования идут в порядке секций.
    assert markup.inline_keyboard[0][0].text == SECTION_LABELS["word"]
    assert markup.inline_keyboard[0][0].copy_text.text == "set (a set of tools)"
    assert markup.inline_keyboard[1][0].text == SECTION_LABELS["translation"]
    assert markup.inline_keyboard[1][0].copy_text.text == "набор, множество"
    assert markup.inline_keyboard[2][0].text == SECTION_LABELS["definition"]
    assert markup.inline_keyboard[2][0].copy_text.text == "a group of things"


def test_phrase_two_buttons():
    sections = [("phrase", "good morning"), ("translation", "доброе утро")]
    markup = build_copy_keyboard(sections)
    assert markup.inline_keyboard[0][0].text == SECTION_LABELS["phrase"]
    assert markup.inline_keyboard[1][0].text == SECTION_LABELS["translation"]


def test_skips_absent_sections():
    # Нет примера/определения — секций меньше, чем «полный» набор.
    sections = [("word", "set"), ("translation", "набор")]
    markup = build_copy_keyboard(sections)
    assert len(markup.inline_keyboard) == 2
    assert markup.inline_keyboard[0][0].copy_text.text == "set"
