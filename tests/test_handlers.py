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


async def test_handle_word_word_path(monkeypatch):
    # Словарь отдал переводы и пример, Free Dictionary — определение.
    async def fake_dictionary(session, word):
        return (["набор", "множество"], "a set of tools")

    async def fake_definition(session, word):
        return "a group of things"

    translate = AsyncMock(return_value="не должно зваться")
    monkeypatch.setattr(h, "fetch_yandex_dictionary", fake_dictionary)
    monkeypatch.setattr(h, "fetch_free_definition", fake_definition)
    monkeypatch.setattr(h, "fetch_yandex_translate", translate)

    message = AsyncMock()
    message.text = "set"
    await h.handle_word(message, http_session=AsyncMock())

    # Машинный перевод не нужен — словарь дал варианты.
    translate.assert_not_called()

    text = message.answer.call_args.args[0]
    assert text == "set (a set of tools)\nнабор, множество\na group of things"

    markup = message.answer.call_args.kwargs["reply_markup"]
    assert len(markup.inline_keyboard) == 3
    assert markup.inline_keyboard[0][0].copy_text.text == "set (a set of tools)"
    assert markup.inline_keyboard[1][0].copy_text.text == "набор, множество"
    assert markup.inline_keyboard[2][0].copy_text.text == "a group of things"


async def test_handle_word_phrase_path(monkeypatch):
    translate = AsyncMock(return_value="доброе утро")
    dictionary = AsyncMock(return_value=([], None))
    definition = AsyncMock(return_value="не должно зваться")
    monkeypatch.setattr(h, "fetch_yandex_translate", translate)
    monkeypatch.setattr(h, "fetch_yandex_dictionary", dictionary)
    monkeypatch.setattr(h, "fetch_free_definition", definition)

    message = AsyncMock()
    message.text = "good morning"
    await h.handle_word(message, http_session=AsyncMock())

    # Для фразы звать только перевод; словарь и определение не нужны.
    translate.assert_called_once()
    dictionary.assert_not_called()
    definition.assert_not_called()

    text = message.answer.call_args.args[0]
    assert text == "good morning\nдоброе утро"
    markup = message.answer.call_args.kwargs["reply_markup"]
    assert len(markup.inline_keyboard) == 2
    assert markup.inline_keyboard[0][0].text == "📋 Фраза"


async def test_handle_word_fallback_to_translate(monkeypatch):
    # Словарь пуст → фолбэк машинным переводом.
    async def fake_dictionary(session, word):
        return ([], None)

    async def fake_definition(session, word):
        return None

    translate = AsyncMock(return_value="перевод")
    monkeypatch.setattr(h, "fetch_yandex_dictionary", fake_dictionary)
    monkeypatch.setattr(h, "fetch_free_definition", fake_definition)
    monkeypatch.setattr(h, "fetch_yandex_translate", translate)

    message = AsyncMock()
    message.text = "obscure"
    await h.handle_word(message, http_session=AsyncMock())

    translate.assert_called_once()
    text = message.answer.call_args.args[0]
    assert text == "obscure\nперевод"  # нет ни примера, ни определения


async def test_handle_word_no_translation_error(monkeypatch):
    translate = AsyncMock(return_value=None)
    monkeypatch.setattr(h, "fetch_yandex_translate", translate)

    message = AsyncMock()
    message.text = "good morning"  # фраза: единственный источник — перевод
    await h.handle_word(message, http_session=AsyncMock())

    sent = message.answer.call_args.args[0]
    assert "Не удалось перевести" in sent
    assert "good morning" in sent
