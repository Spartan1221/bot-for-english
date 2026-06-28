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
    # Free Dictionary отдал определение + пример, Yandex Dictionary — варианты перевода.
    async def fake_free_definition(session, word):
        return ("a group of things", "a set of tools")

    async def fake_dictionary(session, word):
        return ["набор", "множество"]

    translate = AsyncMock(return_value="не должно зваться")
    monkeypatch.setattr(h, "fetch_free_definition", fake_free_definition)
    monkeypatch.setattr(h, "fetch_yandex_dictionary", fake_dictionary)
    monkeypatch.setattr(h, "fetch_yandex_translate", translate)

    message = AsyncMock()
    message.text = "set"
    await h.handle_word(message, http_session=AsyncMock())

    translate.assert_not_called()  # словарь дал варианты — перевод не нужен

    text = message.answer.call_args.args[0]
    # Ответ — таблица, содержащая все три секции.
    for value in ("set (a set of tools)", "набор, множество", "a group of things"):
        assert value in text
    assert "|" in text

    markup = message.answer.call_args.kwargs["reply_markup"]
    assert len(markup.inline_keyboard) == 3
    assert markup.inline_keyboard[0][0].copy_text.text == "set (a set of tools)"
    assert markup.inline_keyboard[1][0].copy_text.text == "набор, множество"
    assert markup.inline_keyboard[2][0].copy_text.text == "a group of things"


async def test_handle_word_phrase_path(monkeypatch):
    translate = AsyncMock(return_value="доброе утро")
    dictionary = AsyncMock(return_value=[])
    free_def = AsyncMock(return_value=(None, None))
    monkeypatch.setattr(h, "fetch_yandex_translate", translate)
    monkeypatch.setattr(h, "fetch_yandex_dictionary", dictionary)
    monkeypatch.setattr(h, "fetch_free_definition", free_def)

    message = AsyncMock()
    message.text = "good morning"
    await h.handle_word(message, http_session=AsyncMock())

    # Для фразы звать только перевод.
    translate.assert_called_once()
    dictionary.assert_not_called()
    free_def.assert_not_called()

    text = message.answer.call_args.args[0]
    assert "good morning" in text
    assert "доброе утро" in text
    markup = message.answer.call_args.kwargs["reply_markup"]
    assert len(markup.inline_keyboard) == 2
    assert markup.inline_keyboard[0][0].text == "📋 Фраза"


async def test_handle_word_strips_article(monkeypatch):
    # 'to go' должно искать слово 'go' (артикль/частица отброшена).
    seen = {}

    async def fake_free_definition(session, word):
        seen["word"] = word
        return (None, None)

    async def fake_dictionary(session, word):
        seen["word"] = word
        return [f"перевод-{word}"]

    monkeypatch.setattr(h, "fetch_free_definition", fake_free_definition)
    monkeypatch.setattr(h, "fetch_yandex_dictionary", fake_dictionary)
    monkeypatch.setattr(h, "fetch_yandex_translate", AsyncMock(return_value=None))

    message = AsyncMock()
    message.text = "to go"
    await h.handle_word(message, http_session=AsyncMock())

    assert seen["word"] == "go"  # lookup шёл по голове слова, а не по 'to go'
    text = message.answer.call_args.args[0]
    assert "перевод-go" in text
    assert "to go" not in text  # отброшенная частица в ответе не видна


async def test_handle_word_fallback_to_translate(monkeypatch):
    # Словарь пуст и Free Dictionary пуст → фолбэк машинным переводом.
    async def fake_free_definition(session, word):
        return (None, None)

    async def fake_dictionary(session, word):
        return []

    translate = AsyncMock(return_value="перевод")
    monkeypatch.setattr(h, "fetch_free_definition", fake_free_definition)
    monkeypatch.setattr(h, "fetch_yandex_dictionary", fake_dictionary)
    monkeypatch.setattr(h, "fetch_yandex_translate", translate)

    message = AsyncMock()
    message.text = "obscure"
    await h.handle_word(message, http_session=AsyncMock())

    translate.assert_called_once()
    text = message.answer.call_args.args[0]
    assert "obscure" in text and "перевод" in text  # ни примера, ни значения


async def test_handle_word_no_translation_error(monkeypatch):
    translate = AsyncMock(return_value=None)
    monkeypatch.setattr(h, "fetch_yandex_translate", translate)

    message = AsyncMock()
    message.text = "good morning"  # фраза: единственный источник — перевод
    await h.handle_word(message, http_session=AsyncMock())

    sent = message.answer.call_args.args[0]
    assert "Не удалось перевести" in sent
    assert "good morning" in sent
