"""Слой взаимодействия с внешними API: Dictionary API и MyMemory."""

from __future__ import annotations

import asyncio
import logging

import aiohttp

from .config import DICT_URL, TRANSLATE_URL

log = logging.getLogger(__name__)


class WordNotFound(Exception):
    """В словаре нет записи для запрошенного слова/фразы."""


async def fetch_definition(
    session: aiohttp.ClientSession, query: str
) -> tuple[str, str | None]:
    """
    Запрос определения в Dictionary API.

    Возвращает кортеж (определение, пример). Поле «пример» равно None,
    если у определения нет примера использования. Бросает WordNotFound,
    если слово не найдено (HTTP 404 или пустой/некорректный ответ).
    """
    url = DICT_URL.format(word=query)
    async with session.get(url) as resp:
        # 404 — штатная ситуация «нет записи», а не транспортная ошибка.
        if resp.status == 404:
            raise WordNotFound(query)
        resp.raise_for_status()  # 4xx/5xx → ClientResponseError
        data = await resp.json()

    if not isinstance(data, list) or not data:
        raise WordNotFound(query)

    return pick_definition(data)


def pick_definition(entries: list) -> tuple[str, str | None] | None:
    """
    Выбирает определение из ответа Dictionary API.

    Среди всех значений предпочитает то, у которого есть пример использования.
    Если примеров нет вообще — берёт первое попавшееся определение.
    Возвращает (определение, пример) или None, если определений нет.
    """
    fallback: tuple[str, str | None] | None = None
    for entry in entries:
        for meaning in entry.get("meanings", []):
            for definition in meaning.get("definitions", []):
                text = (definition.get("definition") or "").strip()
                if not text:
                    continue
                example = (definition.get("example") or "").strip() or None
                if fallback is None:
                    fallback = (text, example)
                if example:  # нашлись и определение, и пример — берём сразу
                    return (text, example)
    return fallback


async def fetch_translation(
    session: aiohttp.ClientSession, text: str
) -> str | None:
    """
    Перевод английского слова/фразы на русский через MyMemory API.

    Перевод — best-effort: при любой ошибке сети/таймаута/квоты возвращаем None,
    чтобы отсутствие перевода не ломало формирование ответа.
    """
    params = {"q": text, "langpair": "en|ru"}
    try:
        async with session.get(TRANSLATE_URL, params=params) as resp:
            resp.raise_for_status()
            data = await resp.json()
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
        log.warning("Перевод не удался для %r: %s", text, exc)
        return None

    translated = (
        data.get("responseData", {}).get("translatedText") or ""
    ).strip()
    # При исчерпании дневного лимита MyMemory возвращает текст-предупреждение.
    if not translated or translated.upper().startswith("MYMEMORY WARNING"):
        log.warning("MyMemory вернул предупреждение/пустой перевод: %r", translated)
        return None
    return translated
