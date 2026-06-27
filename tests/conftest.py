"""Общие фикстуры и заглушки для тестов.

Чтобы не ходить в сеть и не тащить зависимость aioresponses, имитируем
минимальный интерфейс aiohttp, который реально используется в bot/api.py:
`async with session.get(url, params=...) as resp` + resp.status/raise_for_status/json().
"""

from __future__ import annotations

import aiohttp
import pytest


class FakeResponse:
    """Имитация ответа aiohttp для `async with session.get(...) as resp`."""

    def __init__(self, *, status: int = 200, json_data=None, enter_exc=None):
        self.status = status
        self._json_data = json_data
        self._enter_exc = enter_exc  # исключение, которое бросается при входе в контекст

    async def __aenter__(self):
        if self._enter_exc is not None:
            raise self._enter_exc
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self):
        if self.status >= 400:
            # Берём базовый класс: его ловят и api.py, и хэндлеры.
            raise aiohttp.ClientError(f"HTTP {self.status}")

    async def json(self):
        return self._json_data


class FakeSession:
    """Минимальная замена aiohttp.ClientSession по используемому интерфейсу."""

    def __init__(self, responses):
        # responses: dict {подстрока URL: FakeResponse}
        # либо callable(url, params) -> FakeResponse
        self._responses = responses
        self.requests: list[tuple[str, dict | None]] = []

    def get(self, url, params=None):
        self.requests.append((url, params))
        if callable(self._responses):
            return self._responses(url, params)
        for key, response in self._responses.items():
            if key in url:
                return response
        raise AssertionError(f"Нет заглушённого ответа для URL: {url}")


@pytest.fixture
def make_response():
    """Фабрика объектов FakeResponse: make_response(status=..., json_data=..., enter_exc=...)."""
    return FakeResponse


@pytest.fixture
def fake_session_factory():
    """Возвращает функцию make(responses) -> FakeSession."""
    return lambda responses: FakeSession(responses)
