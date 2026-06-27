"""Слой взаимодействия с внешними API: Yandex Cloud Translate, Yandex Dictionary, Free Dictionary."""

from __future__ import annotations

import asyncio
import logging

import aiohttp

from .config import (
    DICT_URL,
    YANDEX_CLOUD_API_KEY,
    YANDEX_DICT_API_KEY,
    YANDEX_DICT_URL,
    YANDEX_FOLDER_ID,
    YANDEX_TRANSLATE_URL,
)

log = logging.getLogger(__name__)

# Сколько максимум вариантов перевода оставлять (дедуп с сохранением порядка).
MAX_TRANSLATIONS = 8


# --------------------------------------------------------------------------- #
#  Yandex Cloud Translate — перевод слов и предложений
# --------------------------------------------------------------------------- #
async def fetch_yandex_translate(
    session: aiohttp.ClientSession, text: str
) -> str | None:
    """
    Перевод текста (слово или фраза) с английского на русский через Yandex Cloud Translate.

    Best-effort: при любой ошибке сети/таймаута/квоты возвращает None, чтобы отсутствие
    перевода не ломало формирование ответа.
    """
    headers = {"Authorization": f"Api-Key {YANDEX_CLOUD_API_KEY}"}
    body = {
        "folderId": YANDEX_FOLDER_ID,
        "texts": [text],
        "sourceLanguageCode": "en",
        "targetLanguageCode": "ru",
    }
    try:
        async with session.post(YANDEX_TRANSLATE_URL, headers=headers, json=body) as resp:
            resp.raise_for_status()
            data = await resp.json()
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
        log.warning("Yandex Translate не сработал для %r: %s", text, exc)
        return None

    try:
        translated = data["translations"][0]["text"].strip()
    except (KeyError, IndexError, TypeError, AttributeError):
        log.warning("Неожиданный ответ Yandex Translate для %r: %s", text, data)
        return None
    return translated or None


# --------------------------------------------------------------------------- #
#  Yandex Dictionary — переводы по частям речи + пример для отдельного слова
# --------------------------------------------------------------------------- #
def parse_dictionary(data: dict) -> tuple[list[str], str | None]:
    """
    Разбирает ответ Yandex Dictionary.

    Возвращает (варианты_перевода, пример). Варианты собираются из переводов всех
    частей речи (def[].tr[].text) и их синонимов (def[].tr[].syn[].text), дедупятся
    с сохранением порядка и обрезаются до MAX_TRANSLATIONS. Пример — первый попавшийся
    def[].tr[].ex[].text. Если данных нет — ([], None).
    """
    translations: list[str] = []
    example: str | None = None

    for def_entry in data.get("def", []):
        for tr in def_entry.get("tr", []):
            for text in (tr.get("text"),):
                if text and text not in translations:
                    translations.append(text)
            for syn in tr.get("syn", []):
                text = syn.get("text")
                if text and text not in translations:
                    translations.append(text)
            if example is None:
                for ex in tr.get("ex", []):
                    ex_text = ex.get("text")
                    if ex_text:
                        example = ex_text
                        break

    return translations[:MAX_TRANSLATIONS], example


async def fetch_yandex_dictionary(
    session: aiohttp.ClientSession, word: str
) -> tuple[list[str], str | None]:
    """
    Словарный lookup слова в Yandex Dictionary: переводы по частям речи + пример.

    Возвращает ([], None), если у слова нет словарной статьи (404/пустой def) или при
    ошибке сети — это не критично, фолбэком послужит машинный перевод.
    """
    params = {"key": YANDEX_DICT_API_KEY, "lang": "en-ru", "text": word}
    try:
        async with session.get(YANDEX_DICT_URL, params=params) as resp:
            if resp.status == 404:
                return [], None
            resp.raise_for_status()
            data = await resp.json()
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
        log.warning("Yandex Dictionary не сработал для %r: %s", word, exc)
        return [], None

    return parse_dictionary(data or {})


# --------------------------------------------------------------------------- #
#  Free Dictionary API — английское определение (значение) отдельного слова
# --------------------------------------------------------------------------- #
def pick_definition(entries: list) -> str | None:
    """Возвращает первое непустое определение из ответа Free Dictionary API или None."""
    for entry in entries:
        for meaning in entry.get("meanings", []):
            for definition in meaning.get("definitions", []):
                text = (definition.get("definition") or "").strip()
                if text:
                    return text
    return None


async def fetch_free_definition(
    session: aiohttp.ClientSession, word: str
) -> str | None:
    """
    Английское определение слова через Free Dictionary API.

    Best-effort: 404/ошибка/пустой ответ → None (определение не обязательно —
    для многих слов его просто нет, и это не ошибка).
    """
    url = DICT_URL.format(word=word)
    try:
        async with session.get(url) as resp:
            if resp.status == 404:
                return None
            resp.raise_for_status()
            data = await resp.json()
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
        log.warning("Free Dictionary не сработал для %r: %s", word, exc)
        return None

    if not isinstance(data, list) or not data:
        return None
    return pick_definition(data)
