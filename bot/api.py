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
    if not translated or translated.lower() == text.strip().lower():
        # Cloud Translate отдаёт исходный текст как есть, когда не может перевести
        # (напр. бессмысленный набор букв) — это не перевод.
        return None
    return translated


# --------------------------------------------------------------------------- #
#  Yandex Dictionary — переводы по частям речи для отдельного слова
# --------------------------------------------------------------------------- #
def parse_dictionary(data: dict) -> list[str]:
    """
    Разбирает ответ Yandex Dictionary: возвращает варианты перевода.

    Варианты собираются из переводов всех частей речи (def[].tr[].text) и их
    синонимов (def[].tr[].syn[].text), дедупятся с сохранением порядка и обрезаются
    до MAX_TRANSLATIONS. Примеры Yandex Dictionary в ответе не отдаёт — их берём из
    Free Dictionary API.
    """
    translations: list[str] = []

    for def_entry in data.get("def", []):
        for tr in def_entry.get("tr", []):
            text = tr.get("text")
            if text and text not in translations:
                translations.append(text)
            for syn in tr.get("syn", []):
                text = syn.get("text")
                if text and text not in translations:
                    translations.append(text)

    return translations[:MAX_TRANSLATIONS]


async def fetch_yandex_dictionary(
    session: aiohttp.ClientSession, word: str
) -> list[str]:
    """
    Словарный lookup слова в Yandex Dictionary: переводы по частям речи.

    Возвращает [], если у слова нет словарной статьи (404/пустой def) или при ошибке
    сети — это не критично, фолбэком послужит машинный перевод.
    """
    params = {"key": YANDEX_DICT_API_KEY, "lang": "en-ru", "text": word}
    try:
        async with session.get(YANDEX_DICT_URL, params=params) as resp:
            if resp.status == 404:
                return []
            resp.raise_for_status()
            data = await resp.json()
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
        log.warning("Yandex Dictionary не сработал для %r: %s", word, exc)
        return []

    return parse_dictionary(data or {})


# --------------------------------------------------------------------------- #
#  Free Dictionary API — английское определение (значение) + пример употребления
# --------------------------------------------------------------------------- #
def pick_definition(entries: list) -> tuple[str | None, str | None]:
    """
    Возвращает (определение, пример) из ответа Free Dictionary API.

    Предпочитает определение, у которого сразу есть пример употребления; если
    примеров нет вообще — берёт первое непустое определение, а пример = None.
    """
    fallback_def: str | None = None
    for entry in entries:
        for meaning in entry.get("meanings", []):
            for definition in meaning.get("definitions", []):
                text = (definition.get("definition") or "").strip()
                if not text:
                    continue
                if fallback_def is None:
                    fallback_def = text
                example = (definition.get("example") or "").strip() or None
                if example:
                    return text, example
    return fallback_def, None


async def fetch_free_definition(
    session: aiohttp.ClientSession, word: str
) -> tuple[str | None, str | None]:
    """
    Английское определение и пример слова через Free Dictionary API.

    Best-effort: 404/ошибка/пустой ответ → (None, None) (для многих слов статьи нет —
    это не ошибка, ответ просто будет без строки значения).
    """
    url = DICT_URL.format(word=word)
    try:
        async with session.get(url) as resp:
            if resp.status == 404:
                return None, None
            resp.raise_for_status()
            data = await resp.json()
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
        log.warning("Free Dictionary не сработал для %r: %s", word, exc)
        return None, None

    if not isinstance(data, list) or not data:
        return None, None
    return pick_definition(data)
