"""Тесты API-слоя: parse_dictionary/pick_definition (чистые) и fetch_* (с фейковой сессией)."""

from __future__ import annotations

import asyncio

import aiohttp

from bot.api import (
    fetch_free_definition,
    fetch_yandex_dictionary,
    fetch_yandex_translate,
    parse_dictionary,
    pick_definition,
)


# --------------------------------------------------------------------------- #
#  parse_dictionary — чистая функция (только переводы)
# --------------------------------------------------------------------------- #
class TestParseDictionary:
    def test_translations_from_tr(self):
        data = {"def": [{"tr": [{"text": "набор"}, {"text": "множество"}]}]}
        assert parse_dictionary(data) == ["набор", "множество"]

    def test_includes_synonyms_and_dedups(self):
        data = {"def": [
            {"pos": "noun", "tr": [{"text": "набор", "syn": [{"text": "комплект"}, {"text": "набор"}]}]},
            {"pos": "verb", "tr": [{"text": "устанавливать", "syn": [{"text": "задавать"}]}]},
        ]}
        assert parse_dictionary(data) == ["набор", "комплект", "устанавливать", "задавать"]

    def test_empty_def(self):
        assert parse_dictionary({"def": []}) == []
        assert parse_dictionary({}) == []

    def test_caps_translations(self):
        # Больше вариантов, чем лимит — обрезаем.
        data = {"def": [{"tr": [{"text": f"t{i}"} for i in range(20)]}]}
        assert len(parse_dictionary(data)) == 8


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
#  fetch_yandex_translate — POST к Cloud Translate, best-effort
# --------------------------------------------------------------------------- #
class TestFetchYandexTranslate:
    async def test_translation_ok(self, fake_session_factory, make_response):
        session = fake_session_factory({
            "translate.api.cloud.yandex.net": make_response(
                status=200,
                json_data={"translations": [{"text": "доброе утро"}]},
            ),
        })
        assert await fetch_yandex_translate(session, "good morning") == "доброе утро"

    async def test_untranslatable_returns_none(self, fake_session_factory, make_response):
        # Cloud отдал текст без изменений — значит перевести не смог (напр. бессмысленный ввод).
        session = fake_session_factory({
            "translate.api.cloud.yandex.net": make_response(
                status=200, json_data={"translations": [{"text": "asdfqwerty"}]},
            ),
        })
        assert await fetch_yandex_translate(session, "asdfqwerty") is None

    async def test_sends_auth_header_and_folder(self, fake_session_factory, make_response):
        session = fake_session_factory({
            "translate.api.cloud.yandex.net": make_response(
                status=200, json_data={"translations": [{"text": "привет"}]}
            ),
        })
        await fetch_yandex_translate(session, "hi")
        req = session.requests[0]
        assert req["method"] == "POST"
        assert req["headers"]["Authorization"].startswith("Api-Key ")
        assert req["json"]["texts"] == ["hi"]
        assert req["json"]["targetLanguageCode"] == "ru"
        assert "folderId" in req["json"]

    async def test_server_error_returns_none(self, fake_session_factory, make_response):
        session = fake_session_factory({
            "translate.api.cloud.yandex.net": make_response(status=500, json_data=None),
        })
        assert await fetch_yandex_translate(session, "hi") is None

    async def test_timeout_returns_none(self, fake_session_factory, make_response):
        session = fake_session_factory({
            "translate.api.cloud.yandex.net": make_response(enter_exc=asyncio.TimeoutError()),
        })
        assert await fetch_yandex_translate(session, "hi") is None

    async def test_malformed_response_returns_none(self, fake_session_factory, make_response):
        session = fake_session_factory({
            "translate.api.cloud.yandex.net": make_response(status=200, json_data={"unexpected": 1}),
        })
        assert await fetch_yandex_translate(session, "hi") is None


# --------------------------------------------------------------------------- #
#  fetch_yandex_dictionary — GET, best-effort (только переводы)
# --------------------------------------------------------------------------- #
class TestFetchYandexDictionary:
    async def test_found(self, fake_session_factory, make_response):
        data = {"def": [{"tr": [{"text": "набор", "syn": [{"text": "комплект"}]}]}]}
        session = fake_session_factory({
            "dictionary.yandex.net": make_response(status=200, json_data=data),
        })
        assert await fetch_yandex_dictionary(session, "set") == ["набор", "комплект"]
        assert session.requests[0]["params"]["lang"] == "en-ru"
        assert session.requests[0]["params"]["text"] == "set"

    async def test_not_found_404(self, fake_session_factory, make_response):
        session = fake_session_factory({
            "dictionary.yandex.net": make_response(status=404, json_data={"def": []}),
        })
        assert await fetch_yandex_dictionary(session, "asdfqwerty") == []

    async def test_empty_def(self, fake_session_factory, make_response):
        session = fake_session_factory({
            "dictionary.yandex.net": make_response(status=200, json_data={"def": []}),
        })
        assert await fetch_yandex_dictionary(session, "x") == []

    async def test_error_returns_empty(self, fake_session_factory, make_response):
        session = fake_session_factory({
            "dictionary.yandex.net": make_response(enter_exc=asyncio.TimeoutError()),
        })
        assert await fetch_yandex_dictionary(session, "x") == []


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
