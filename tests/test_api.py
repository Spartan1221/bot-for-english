"""Тесты API-слоя: parse_dictionary/pick_definition (чистые) и fetch_* (с фейковой сессией)."""

from __future__ import annotations

import asyncio

import aiohttp

from bot.api import (
    fetch_free_definition,
    fetch_microsoft_translate,
    fetch_yandex_dictionary,
    parse_dictionary,
    pick_definition,
)


# --------------------------------------------------------------------------- #
#  parse_dictionary — чистая функция (фильтр по частям речи)
# --------------------------------------------------------------------------- #
class TestParseDictionary:
    def _data(self):
        # статья сразу с существительным и глаголом
        return {"def": [
            {"pos": "noun", "tr": [{"text": "книга", "syn": [{"text": "книжка"}]}]},
            {"pos": "verb", "tr": [{"text": "бронировать", "syn": [{"text": "забронировать"}]}]},
        ]}

    def test_noun_only(self):
        assert parse_dictionary(self._data(), ["noun"]) == ["книга", "книжка"]

    def test_verb_only(self):
        assert parse_dictionary(self._data(), ["verb"]) == ["бронировать", "забронировать"]

    def test_both_noun_then_verb(self):
        # без артикля: и noun, и verb; порядок noun раньше verb.
        assert parse_dictionary(self._data(), ["noun", "verb"]) == [
            "книга", "книжка", "бронировать", "забронировать",
        ]

    def test_dedups(self):
        data = {"def": [{"pos": "noun", "tr": [
            {"text": "книга"}, {"text": "книга"}, {"text": "том"},
        ]}]}
        assert parse_dictionary(data, ["noun"]) == ["книга", "том"]

    def test_empty(self):
        assert parse_dictionary({"def": []}, ["noun", "verb"]) == []
        assert parse_dictionary({}, ["noun"]) == []

    def test_caps(self):
        # Больше вариантов, чем лимит — обрезаем.
        data = {"def": [{"pos": "noun", "tr": [{"text": f"t{i}"} for i in range(20)]}]}
        assert len(parse_dictionary(data, ["noun"])) == 8

    def test_balances_pos_when_capped(self):
        # Много существительных и глаголов — лимит делится поровну, обе части речи видны.
        data = {"def": [
            {"pos": "noun", "tr": [{"text": f"n{i}"} for i in range(6)]},
            {"pos": "verb", "tr": [{"text": f"v{i}"} for i in range(6)]},
        ]}
        out = parse_dictionary(data, ["noun", "verb"])
        assert len(out) == 8  # 4 noun + 4 verb
        assert any(x.startswith("n") for x in out)
        assert any(x.startswith("v") for x in out)


# --------------------------------------------------------------------------- #
#  pick_definition — чистая функция (определение + пример)
# --------------------------------------------------------------------------- #
class TestPickDefinition:
    def test_prefers_definition_with_example(self):
        entries = [{"meanings": [{"definitions": [
            {"definition": "first def"},
            {"definition": "second def", "example": "An example."},
        ]}]}]
        assert pick_definition(entries) == ("second def", "An example.")

    def test_falls_back_without_example(self):
        entries = [{"meanings": [{"definitions": [{"definition": "only def"}]}]}]
        assert pick_definition(entries) == ("only def", None)

    def test_skips_empty_definitions(self):
        entries = [{"meanings": [{"definitions": [
            {"definition": ""},
            {"definition": "real def", "example": "ex"},
        ]}]}]
        assert pick_definition(entries) == ("real def", "ex")

    def test_none_when_absent(self):
        assert pick_definition([]) == (None, None)
        assert pick_definition([{"word": "x"}]) == (None, None)


# --------------------------------------------------------------------------- #
#  fetch_microsoft_translate — POST к Azure Translator, best-effort
# --------------------------------------------------------------------------- #
class TestFetchMicrosoftTranslate:
    async def test_translation_ok(self, fake_session_factory, make_response):
        session = fake_session_factory({
            "microsofttranslator.com": make_response(
                status=200,
                json_data=[{"translations": [{"text": "доброе утро", "to": "ru"}]}],
            ),
        })
        assert await fetch_microsoft_translate(session, "good morning") == "доброе утро"

    async def test_sends_key_region_and_body(self, fake_session_factory, make_response):
        session = fake_session_factory({
            "microsofttranslator.com": make_response(
                status=200, json_data=[{"translations": [{"text": "привет", "to": "ru"}]}],
            ),
        })
        await fetch_microsoft_translate(session, "hi")
        req = session.requests[0]
        assert req["method"] == "POST"
        assert req["headers"]["Ocp-Apim-Subscription-Key"]
        assert req["headers"]["Ocp-Apim-Subscription-Region"]
        assert req["json"] == [{"Text": "hi"}]

    async def test_untranslatable_returns_none(self, fake_session_factory, make_response):
        # Переводчик вернул текст без изменений — значит перевести не смог.
        session = fake_session_factory({
            "microsofttranslator.com": make_response(
                status=200, json_data=[{"translations": [{"text": "asdfqwerty"}]}],
            ),
        })
        assert await fetch_microsoft_translate(session, "asdfqwerty") is None

    async def test_server_error_returns_none(self, fake_session_factory, make_response):
        session = fake_session_factory({
            "microsofttranslator.com": make_response(status=500, json_data=None),
        })
        assert await fetch_microsoft_translate(session, "hi") is None

    async def test_timeout_returns_none(self, fake_session_factory, make_response):
        session = fake_session_factory({
            "microsofttranslator.com": make_response(enter_exc=asyncio.TimeoutError()),
        })
        assert await fetch_microsoft_translate(session, "hi") is None

    async def test_malformed_response_returns_none(self, fake_session_factory, make_response):
        session = fake_session_factory({
            "microsofttranslator.com": make_response(status=200, json_data={"unexpected": 1}),
        })
        assert await fetch_microsoft_translate(session, "hi") is None


# --------------------------------------------------------------------------- #
#  fetch_yandex_dictionary — GET с фильтром по частям речи, best-effort
# --------------------------------------------------------------------------- #
class TestFetchYandexDictionary:
    async def test_found_with_pos_filter(self, fake_session_factory, make_response):
        data = {"def": [
            {"pos": "noun", "tr": [{"text": "книга"}]},
            {"pos": "verb", "tr": [{"text": "бронировать"}]},
        ]}
        session = fake_session_factory({
            "dictionary.yandex.net": make_response(status=200, json_data=data),
        })
        # Запросили только существительные переводы.
        assert await fetch_yandex_dictionary(session, "book", ["noun"]) == ["книга"]
        assert session.requests[0]["params"]["lang"] == "en-ru"
        assert session.requests[0]["params"]["text"] == "book"

    async def test_not_found_404(self, fake_session_factory, make_response):
        session = fake_session_factory({
            "dictionary.yandex.net": make_response(status=404, json_data={"def": []}),
        })
        assert await fetch_yandex_dictionary(session, "asdfqwerty", ["noun", "verb"]) == []

    async def test_empty_def(self, fake_session_factory, make_response):
        session = fake_session_factory({
            "dictionary.yandex.net": make_response(status=200, json_data={"def": []}),
        })
        assert await fetch_yandex_dictionary(session, "x", ["noun"]) == []

    async def test_error_returns_empty(self, fake_session_factory, make_response):
        session = fake_session_factory({
            "dictionary.yandex.net": make_response(enter_exc=asyncio.TimeoutError()),
        })
        assert await fetch_yandex_dictionary(session, "x", ["noun"]) == []


# --------------------------------------------------------------------------- #
#  fetch_free_definition — GET, best-effort (определение + пример)
# --------------------------------------------------------------------------- #
class TestFetchFreeDefinition:
    async def test_found_with_example(self, fake_session_factory, make_response):
        entries = [{"meanings": [{"definitions": [
            {"definition": "a group of things", "example": "a set of tools"},
        ]}]}]
        session = fake_session_factory({
            "dictionaryapi.dev": make_response(status=200, json_data=entries),
        })
        assert await fetch_free_definition(session, "set") == ("a group of things", "a set of tools")

    async def test_found_without_example(self, fake_session_factory, make_response):
        entries = [{"meanings": [{"definitions": [{"definition": "just a def"}]}]}]
        session = fake_session_factory({
            "dictionaryapi.dev": make_response(status=200, json_data=entries),
        })
        assert await fetch_free_definition(session, "x") == ("just a def", None)

    async def test_not_found_404(self, fake_session_factory, make_response):
        session = fake_session_factory({
            "dictionaryapi.dev": make_response(status=404, json_data={}),
        })
        assert await fetch_free_definition(session, "asdfqwerty") == (None, None)

    async def test_empty_payload(self, fake_session_factory, make_response):
        session = fake_session_factory({
            "dictionaryapi.dev": make_response(status=200, json_data=[]),
        })
        assert await fetch_free_definition(session, "x") == (None, None)

    async def test_error_returns_none(self, fake_session_factory, make_response):
        session = fake_session_factory({
            "dictionaryapi.dev": make_response(enter_exc=aiohttp.ClientError("boom")),
        })
        assert await fetch_free_definition(session, "x") == (None, None)
