"""Тесты хэндлеров aiogram (message мокируется, API-вызовы подменяются)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import bot.handlers as h
from bot.config import START_TEXT


def _dict(*entries):
    """Сборка ответа Yandex Dictionary: entries = [(pos, [tr_text, ...]), ...]."""
    return {"def": [{"pos": pos, "tr": [{"text": t} for t in trs]} for pos, trs in entries]}


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


async def test_handle_word_no_article_all_pos(monkeypatch):
    # Слово без артикля — переводы всех присутствующих частей речи (noun + verb).
    async def fake_free_definition(session, word):
        return ("a group of things", "a set of tools")

    seen = {}

    async def fake_dictionary(session, word):
        seen["word"] = word
        return _dict(("noun", ["набор", "комплект"]), ("verb", ["ставить"]))

    translate = AsyncMock(return_value="не должно зваться")
    monkeypatch.setattr(h, "fetch_free_definition", fake_free_definition)
    monkeypatch.setattr(h, "fetch_yandex_dictionary", fake_dictionary)
    monkeypatch.setattr(h, "fetch_yandex_translate", translate)

    message = AsyncMock()
    message.text = "set"
    await h.handle_word(message, http_session=AsyncMock())

    translate.assert_not_called()
    assert seen["word"] == "set"
    text = message.answer.call_args.args[0]
    # и существительные, и глагол видны (баланс лимита по частям речи)
    assert "набор" in text and "комплект" in text and "ставить" in text
    markup = message.answer.call_args.kwargs["reply_markup"]
    assert len(markup.inline_keyboard) == 3
    assert markup.inline_keyboard[0][0].copy_text.text == "set (a set of tools)"
    assert markup.inline_keyboard[2][0].copy_text.text == "a group of things"


async def test_handle_word_article_selects_pos(monkeypatch):
    # a/an/the → только noun; to → только verb (несмотря на прочие POS в статье).
    async def fake_free_definition(session, word):
        return (None, None)

    async def fake_dictionary(session, word):
        return _dict(("noun", ["книга"]), ("verb", ["бронировать"]), ("adjective", ["книжный"]))

    monkeypatch.setattr(h, "fetch_free_definition", fake_free_definition)
    monkeypatch.setattr(h, "fetch_yandex_dictionary", fake_dictionary)
    monkeypatch.setattr(h, "fetch_yandex_translate", AsyncMock(return_value=None))

    message = AsyncMock()
    message.text = "a book"
    await h.handle_word(message, http_session=AsyncMock())
    text = message.answer.call_args.args[0]
    assert "книга" in text and "бронировать" not in text and "книжный" not in text

    message = AsyncMock()
    message.text = "to book"
    await h.handle_word(message, http_session=AsyncMock())
    text = message.answer.call_args.args[0]
    assert "бронировать" in text and "книга" not in text


async def test_handle_word_adjective_multiple_translations(monkeypatch):
    # Прилагательное без артикля — несколько переводов (раньше давало один из Translate).
    async def fake_free_definition(session, word):
        return (None, None)

    async def fake_dictionary(session, word):
        return _dict(("adjective", ["счастливый", "довольный", "приятный"]))

    translate = AsyncMock(return_value="счастливый")
    monkeypatch.setattr(h, "fetch_free_definition", fake_free_definition)
    monkeypatch.setattr(h, "fetch_yandex_dictionary", fake_dictionary)
    monkeypatch.setattr(h, "fetch_yandex_translate", translate)

    message = AsyncMock()
    message.text = "happy"
    await h.handle_word(message, http_session=AsyncMock())

    translate.assert_not_called()  # словарь дал несколько переводов — машинный не нужен
    text = message.answer.call_args.args[0]
    assert "счастливый" in text and "довольный" in text and "приятный" in text


async def test_handle_word_phrase_path(monkeypatch):
    translate = AsyncMock(return_value="доброе утро")
    dictionary = AsyncMock(return_value={})
    free_def = AsyncMock(return_value=(None, None))
    monkeypatch.setattr(h, "fetch_yandex_translate", translate)
    monkeypatch.setattr(h, "fetch_yandex_dictionary", dictionary)
    monkeypatch.setattr(h, "fetch_free_definition", free_def)

    message = AsyncMock()
    message.text = "good morning"
    await h.handle_word(message, http_session=AsyncMock())

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

    async def fake_dictionary(session, word):
        return {}

    translate = AsyncMock(return_value="перевод")
    monkeypatch.setattr(h, "fetch_free_definition", fake_free_definition)
    monkeypatch.setattr(h, "fetch_yandex_dictionary", fake_dictionary)
    monkeypatch.setattr(h, "fetch_yandex_translate", translate)

    message = AsyncMock()
    message.text = "obscure"
    await h.handle_word(message, http_session=AsyncMock())

    translate.assert_called_once()
    text = message.answer.call_args.args[0]
    assert text == "obscure\n-----\nперевод"


async def test_handle_word_no_translation_error(monkeypatch):
    translate = AsyncMock(return_value=None)
    monkeypatch.setattr(h, "fetch_yandex_translate", translate)

    message = AsyncMock()
    message.text = "good morning"  # фраза: единственный источник — перевод
    await h.handle_word(message, http_session=AsyncMock())

    sent = message.answer.call_args.args[0]
    assert "Не удалось перевести" in sent
    assert "good morning" in sent
