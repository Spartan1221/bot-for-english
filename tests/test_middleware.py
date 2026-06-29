"""Тесты middleware доступа и разбора user_id."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from aiogram.types import Message

import bot.middleware as mw
from bot.config import ACCESS_DENIED_TEXT, parse_user_ids
from bot.middleware import AccessMiddleware


class TestParseUserIds:
    def test_single_and_multiple(self):
        assert parse_user_ids("123") == frozenset({123})
        assert parse_user_ids("123, 456") == frozenset({123, 456})

    def test_separators_and_spaces(self):
        assert parse_user_ids("  1 ; 2 ,3 ") == frozenset({1, 2, 3})

    def test_dedups(self):
        assert parse_user_ids("123,123,456") == frozenset({123, 456})

    def test_skips_garbage(self):
        assert parse_user_ids("abc, 123, , x") == frozenset({123})

    def test_empty(self):
        assert parse_user_ids("") == frozenset()
        assert parse_user_ids(None) == frozenset()


def _event(user_id):
    event = MagicMock(spec=Message)
    event.from_user = SimpleNamespace(id=user_id) if user_id is not None else None
    event.answer = AsyncMock()
    return event


class TestAccessMiddleware:
    async def test_allowed_user_passes(self, monkeypatch):
        monkeypatch.setattr(mw, "ALLOWED_USER_IDS", frozenset({123}))
        handler = AsyncMock(return_value="ok")
        result = await AccessMiddleware()(handler, _event(123), {})
        handler.assert_awaited_once()
        assert result == "ok"

    async def test_disallowed_user_blocked_and_answered(self, monkeypatch):
        monkeypatch.setattr(mw, "ALLOWED_USER_IDS", frozenset({123}))
        handler = AsyncMock()
        event = _event(999)
        await AccessMiddleware()(handler, event, {})
        handler.assert_not_called()
        event.answer.assert_awaited_once_with(ACCESS_DENIED_TEXT)

    async def test_empty_whitelist_allows_all(self, monkeypatch):
        monkeypatch.setattr(mw, "ALLOWED_USER_IDS", frozenset())
        handler = AsyncMock(return_value="ok")
        await AccessMiddleware()(handler, _event(999), {})
        handler.assert_awaited_once()

    async def test_no_from_user_blocked(self, monkeypatch):
        monkeypatch.setattr(mw, "ALLOWED_USER_IDS", frozenset({123}))
        handler = AsyncMock()
        event = _event(None)
        await AccessMiddleware()(handler, event, {})
        handler.assert_not_called()
