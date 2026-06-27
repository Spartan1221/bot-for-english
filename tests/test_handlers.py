"""Тесты хэндлеров aiogram (message мокируется, API-вызовы подменяются)."""

from __future__ import annotations

from unittest.mock import AsyncMock

from bot.api import WordNotFound
from bot.config import START_TEXT
from bot.handlers import cmd_start, handle_word


async def test_cmd_start_sends_greeting():
    message = AsyncMock()
    await cmd_start(message)
    message.answer.assert_called_once_with(START_TEXT)


async def test_handle_word_rejects_invalid_input():
    message = AsyncMock()
    message.text = "123"
    await handle_word(message, http_session=AsyncMock())
    assert "только буквы" in message.answer.call_args.args[0]


async def test_handle_word_rejects_empty():
    message = AsyncMock()
    message.text = None
    await handle_word(message, http_session=AsyncMock())
    assert "только буквы" in message.answer.call_args.args[0]


async def test_handle_word_formats_valid_input(monkeypatch):
    async def fake_definition(session, query):
        return ("a nice word", "It is a nice word.")

    async def fake_translation(session, query):
        return "хорошее слово"

    # Подменяем ссылки, импортированные в bot.handlers.
    monkeypatch.setattr("bot.handlers.fetch_definition", fake_definition)
    monkeypatch.setattr("bot.handlers.fetch_translation", fake_translation)

    message = AsyncMock()
    message.text = "serendipity"
    await handle_word(message, http_session=AsyncMock())
    assert message.answer.call_args.args[0] == (
        "serendipity (It is a nice word.)\nхорошее слово (a nice word)"
    )


async def test_handle_word_sends_copy_keyboard(monkeypatch):
    async def fake_definition(session, query):
        return ("a nice word", "It is a nice word.")

    async def fake_translation(session, query):
        return "хорошее слово"

    monkeypatch.setattr("bot.handlers.fetch_definition", fake_definition)
    monkeypatch.setattr("bot.handlers.fetch_translation", fake_translation)

    message = AsyncMock()
    message.text = "serendipity"
    await handle_word(message, http_session=AsyncMock())

    # Под ответом — клавиатура из двух кнопок, копирующих каждую строку.
    markup = message.answer.call_args.kwargs["reply_markup"]
    assert len(markup.inline_keyboard) == 2
    assert markup.inline_keyboard[0][0].copy_text.text == "serendipity (It is a nice word.)"
    assert markup.inline_keyboard[1][0].copy_text.text == "хорошее слово (a nice word)"


async def test_handle_word_reports_not_found(monkeypatch):
    async def fake_definition(session, query):
        raise WordNotFound(query)

    async def fake_translation(session, query):
        return "x"

    monkeypatch.setattr("bot.handlers.fetch_definition", fake_definition)
    monkeypatch.setattr("bot.handlers.fetch_translation", fake_translation)

    message = AsyncMock()
    message.text = "asdfqwerty"
    await handle_word(message, http_session=AsyncMock())
    sent = message.answer.call_args.args[0]
    assert "Не удалось найти" in sent
    assert "asdfqwerty" in sent
