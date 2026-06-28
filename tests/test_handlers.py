"""Тесты хэндлеров aiogram (message мокируется, API-вызовы подменяются)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import bot.handlers as h
from bot.config import START_TEXT


async def test_cmd_start_sends_greeting():
    message = AsyncMock()
    await h.cmd_start(message)
    message.answer.assert_called_once_with(START_TEXT)


async def test_handle_word_rejects_invalid_input():
    message = AsyncMock()
    message.text = "123"
    await h.handle_word(message, http_session=AsyncMock())
    assert "только буквы" in message.answer.call_args.args[0]


async def test_handle_word_rejects_empty():
    message = AsyncMock()
    message.text = None
    await h.handle_word(message, http_session=AsyncMock())
    assert "только буквы" in message.answer.call_args.args[0]


async def test_handle_word_no_article_both_pos(monkeypatch):
    # Слово без артикля → ищем и noun, и verb.
    async def fake_free_definition(session, word):
        return ("a group of things", "a set of tools")

    seen = {}

    async def fake_dictionary(session, word, allowed_pos):
        seen["word"], seen["pos"] = word, allowed_pos
        return ["набор", "множество"]

    translate = AsyncMock(return_value="не должно зваться")
    monkeypatch.setattr(h, "fetch_free_definition", fake_free_definition)
    monkeypatch.setattr(h, "fetch_yandex_dictionary", fake_dictionary)
    monkeypatch.setattr(h, "fetch_microsoft_translate", translate)

    message = AsyncMock()
    message.text = "set"
    await h.handle_word(message, http_session=AsyncMock())

    translate.assert_not_called()  # словарь дал варианты — перевод не нужен
    assert seen == {"word": "set", "pos": ["noun", "verb"]}

    text = message.answer.call_args.args[0]
    assert text == "set (a set of tools)\n-----\nнабор, множество\n-----\na group of things"

    markup = message.answer.call_args.kwargs["reply_markup"]
    assert len(markup.inline_keyboard) == 3
    assert markup.inline_keyboard[0][0].copy_text.text == "set (a set of tools)"
    assert markup.inline_keyboard[1][0].copy_text.text == "набор, множество"
    assert markup.inline_keyboard[2][0].copy_text.text == "a group of things"


async def test_handle_word_article_selects_pos(monkeypatch):
    # 'a book' → артикль a → только noun; 'to book' → только verb.
    seen = {}

    async def fake_free_definition(session, word):
        return (None, None)

    async def fake_dictionary(session, word, allowed_pos):
        seen[word] = allowed_pos
        return [f"перевод-{word}-{'-'.join(allowed_pos)}"]

    monkeypatch.setattr(h, "fetch_free_definition", fake_free_definition)
    monkeypatch.setattr(h, "fetch_yandex_dictionary", fake_dictionary)
    monkeypatch.setattr(h, "fetch_microsoft_translate", AsyncMock(return_value=None))

    for raw, expected_pos in [("a book", ["noun"]), ("to book", ["verb"])]:
        message = AsyncMock()
        message.text = raw
        await h.handle_word(message, http_session=AsyncMock())
        assert seen["book"] == expected_pos
        text = message.answer.call_args.args[0]
        # Голова слова без артикля; перевод соответствует выбранной части речи.
        assert text.startswith("book")
        assert f"перевод-book-{'-'.join(expected_pos)}" in text


async def test_handle_word_phrase_path(monkeypatch):
    translate = AsyncMock(return_value="доброе утро")
    dictionary = AsyncMock(return_value=[])
    free_def = AsyncMock(return_value=(None, None))
    monkeypatch.setattr(h, "fetch_microsoft_translate", translate)
    monkeypatch.setattr(h, "fetch_yandex_dictionary", dictionary)
    monkeypatch.setattr(h, "fetch_free_definition", free_def)

    message = AsyncMock()
    message.text = "good morning"
    await h.handle_word(message, http_session=AsyncMock())

    # Для фразы зовём только машинный перевод.
    translate.assert_called_once()
    dictionary.assert_not_called()
    free_def.assert_not_called()

    text = message.answer.call_args.args[0]
    assert text == "good morning\n-----\nдоброе утро"
    markup = message.answer.call_args.kwargs["reply_markup"]
    assert len(markup.inline_keyboard) == 2
    assert markup.inline_keyboard[0][0].text == "📋 Фраза"


async def test_handle_word_fallback_to_translate(monkeypatch):
    # Словарь пуст и Free Dictionary пуст → фолбэк машинным переводом.
    async def fake_free_definition(session, word):
        return (None, None)

    async def fake_dictionary(session, word, allowed_pos):
        return []

    translate = AsyncMock(return_value="перевод")
    monkeypatch.setattr(h, "fetch_free_definition", fake_free_definition)
    monkeypatch.setattr(h, "fetch_yandex_dictionary", fake_dictionary)
    monkeypatch.setattr(h, "fetch_microsoft_translate", translate)

    message = AsyncMock()
    message.text = "obscure"
    await h.handle_word(message, http_session=AsyncMock())

    translate.assert_called_once()
    text = message.answer.call_args.args[0]
    assert text == "obscure\n-----\nперевод"


async def test_handle_word_no_translation_error(monkeypatch):
    translate = AsyncMock(return_value=None)
    monkeypatch.setattr(h, "fetch_microsoft_translate", translate)

    message = AsyncMock()
    message.text = "good morning"  # фраза: единственный источник — перевод
    await h.handle_word(message, http_session=AsyncMock())

    sent = message.answer.call_args.args[0]
    assert "Не удалось перевести" in sent
    assert "good morning" in sent
