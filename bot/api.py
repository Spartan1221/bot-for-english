"""Слой взаимодействия с внешними API: Microsoft (Azure) Translator, Yandex Dictionary, Free Dictionary."""

from __future__ import annotations

import asyncio
import logging

import aiohttp

from .config import (
    AZURE_TRANSLATE_URL,
    AZURE_TRANSLATOR_KEY,
    AZURE_TRANSLATOR_REGION,
    DICT_URL,
    YANDEX_DICT_API_KEY,
    YANDEX_DICT_URL,
)

log = logging.getLogger(__name__)

# Сколько максимум вариантов перевода оставлять (дедуп с сохранением порядка).
MAX_TRANSLATIONS = 8


# --------------------------------------------------------------------------- #
#  Microsoft (Azure) Translator — перевод слов и предложений
# --------------------------------------------------------------------------- #
async def fetch_microsoft_translate(
    session: aiohttp.ClientSession, text: str
) -> str | None:
    """
    Перевод текста (слово или фраза) с английского на русский через Microsoft Translator.

    Best-effort: при любой ошибке сети/таймаута/квоты возвращает None, чтобы отсутствие
    перевода не ломало формирование ответа.
    """
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_TRANSLATOR_KEY,
        "Ocp-Apim-Subscription-Region": AZURE_TRANSLATOR_REGION,
        "Content-Type": "application/json",
    }
    body = [{"Text": text}]
    try:
        async with session.post(AZURE_TRANSLATE_URL, headers=headers, json=body) as resp:
            resp.raise_for_status()
            data = await resp.json()
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
        log.warning("Microsoft Translator не сработал для %r: %s", text, exc)
        return None

    try:
        translated = data[0]["translations"][0]["text"].strip()
    except (KeyError, IndexError, TypeError, AttributeError):
        log.warning("Неожиданный ответ Microsoft Translator для %r: %s", text, data)
        return None
    if not translated or translated.lower() == text.strip().lower():
        # Переводчик может вернуть исходный текст как есть для непереводимого ввода.
        return None
    return translated


# --------------------------------------------------------------------------- #
#  Yandex Dictionary — переводы отдельного слова, отфильтрованные по части речи
# --------------------------------------------------------------------------- #
def parse_dictionary(data: dict, allowed_pos: list[str]) -> list[str]:
    """
    Варианты перевода из ответа Yandex Dictionary, отфильтрованные по частям речи.

    `allowed_pos` — упорядоченный список (напр. ["noun"], ["verb"], ["noun", "verb"]);
    порядок задаёт очерёдность групп в выводе (noun раньше verb). Берутся
    def[].tr[].text и их синонимы def[].tr[].syn[].text. Лимит делится поровну между
    запрошенными частями речи (MAX_TRANSLATIONS // len(allowed_pos) на каждую), чтобы
    при «noun + verb» обе группы гарантированно попали в ответ, а не вытесняли друг друга.
    Дедуп — глобальный.
    """
    per_pos = max(1, MAX_TRANSLATIONS // max(1, len(allowed_pos)))
    result: list[str] = []
    seen: set[str] = set()
    for pos in allowed_pos:
        group: list[str] = []
        for def_entry in data.get("def", []):
            if def_entry.get("pos") != pos:
                continue
            for tr in def_entry.get("tr", []):
                candidates = [tr.get("text")]
                candidates += [syn.get("text") for syn in tr.get("syn", [])]
                for cand in candidates:
                    if cand and cand not in seen and len(group) < per_pos:
                        seen.add(cand)
                        group.append(cand)
                if len(group) >= per_pos:
                    break
            if len(group) >= per_pos:
                break
        result.extend(group)
    return result


async def fetch_yandex_dictionary(
    session: aiohttp.ClientSession, word: str, allowed_pos: list[str]
) -> list[str]:
    """
    Словарный lookup слова в Yandex Dictionary с фильтром по частям речи.

    Возвращает [], если статьи нет (404/пустой def) или при ошибке сети — не критично,
    фолбэком послужит машинный перевод.
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

    return parse_dictionary(data or {}, allowed_pos)


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
