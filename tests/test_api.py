"""Тесты API-слоя: pick_definition (чистая) и fetch_* (с фейковой сессией)."""

from __future__ import annotations

import asyncio

import aiohttp
import pytest

from bot.api import (
    WordNotFound,
    fetch_definition,
    fetch_translation,
    pick_definition,
)


# --------------------------------------------------------------------------- #
#  pick_definition — чистая функция
# --------------------------------------------------------------------------- #
class TestPickDefinition:
    def test_prefers_definition_with_example(self):
        entries = [{"meanings": [{"definitions": [
            {"definition": "first def"},                            # без примера
            {"definition": "second def", "example": "An example."},  # с примером
        ]}]}]
        definition, example = pick_definition(entries)
        assert definition == "second def"
        assert example == "An example."

    def test_falls_back_to_first_without_example(self):
        entries = [{"meanings": [{"definitions": [{"definition": "only def"}]}]}]
        definition, example = pick_definition(entries)
        assert definition == "only def"
        assert example is None

    def test_empty_entries(self):
        assert pick_definition([]) is None

    def test_missing_meanings_key(self):
        assert pick_definition([{"word": "x"}]) is None

    def test_skips_empty_definitions(self):
        entries = [{"meanings": [{"definitions": [
            {"definition": ""},
            {"definition": "real def", "example": "ex"},
        ]}]}]
        definition, example = pick_definition(entries)
        assert definition == "real def"
        assert example == "ex"


# --------------------------------------------------------------------------- #
#  fetch_definition — с фейковой сессией aiohttp
# --------------------------------------------------------------------------- #
class TestFetchDefinition:
    async def test_found_with_example(self, fake_session_factory, make_response):
        entries = [{"meanings": [{"definitions": [
            {"definition": "a nice word", "example": "It is a nice word."}
        ]}]}]
        session = fake_session_factory({
            "dictionaryapi.dev": make_response(status=200, json_data=entries),
        })
        definition, example = await fetch_definition(session, "serendipity")
        assert definition == "a nice word"
        assert example == "It is a nice word."

    async def test_not_found_404(self, fake_session_factory, make_response):
        session = fake_session_factory({
            "dictionaryapi.dev": make_response(
                status=404, json_data={"title": "No Definitions Found"}
            ),
        })
        with pytest.raises(WordNotFound):
            await fetch_definition(session, "asdfqwerty")

    async def test_empty_payload_raises_not_found(self, fake_session_factory, make_response):
        session = fake_session_factory({
            "dictionaryapi.dev": make_response(status=200, json_data=[]),
        })
        with pytest.raises(WordNotFound):
            await fetch_definition(session, "x")

    async def test_server_error_raises_client_error(self, fake_session_factory, make_response):
        session = fake_session_factory({
            "dictionaryapi.dev": make_response(status=500, json_data=None),
        })
        with pytest.raises(aiohttp.ClientError):
            await fetch_definition(session, "x")


# --------------------------------------------------------------------------- #
#  fetch_translation — best-effort (никогда не бросает, возвращает None)
# --------------------------------------------------------------------------- #
class TestFetchTranslation:
    async def test_translation_ok(self, fake_session_factory, make_response):
        session = fake_session_factory({
            "mymemory.translated.net": make_response(
                status=200,
                json_data={"responseData": {"translatedText": "счастливая случайность"}},
            ),
        })
        assert await fetch_translation(session, "serendipity") == "счастливая случайность"

    async def test_mymemory_warning_returns_none(self, fake_session_factory, make_response):
        session = fake_session_factory({
            "mymemory.translated.net": make_response(
                status=200,
                json_data={"responseData": {"translatedText": "MYMEMORY WARNING: quota exceeded"}},
            ),
        })
        assert await fetch_translation(session, "serendipity") is None

    async def test_empty_translation_returns_none(self, fake_session_factory, make_response):
        session = fake_session_factory({
            "mymemory.translated.net": make_response(
                status=200, json_data={"responseData": {"translatedText": ""}}
            ),
        })
        assert await fetch_translation(session, "serendipity") is None

    async def test_server_error_returns_none(self, fake_session_factory, make_response):
        session = fake_session_factory({
            "mymemory.translated.net": make_response(status=503, json_data=None),
        })
        assert await fetch_translation(session, "serendipity") is None

    async def test_timeout_returns_none(self, fake_session_factory, make_response):
        session = fake_session_factory({
            "mymemory.translated.net": make_response(enter_exc=asyncio.TimeoutError()),
        })
        assert await fetch_translation(session, "serendipity") is None
