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
        # Yandex Translate может вернуть исходный текст как есть для непереводимого ввода.
        return None
    return translated


# --------------------------------------------------------------------------- #
#  Yandex Dictionary — переводы отдельного слова, отфильтрованные по части речи
# --------------------------------------------------------------------------- #
def parse_dictionary(data: dict, allowed_pos: list[str] | None) -> list[str]:
    """
    Варианты перевода из ответа Yandex Dictionary.

    `allowed_pos`:
    - список частей речи (напр. ["noun"], ["verb"]) — переводим только их;
    - None — все присутствующие в статье части речи (для слова без артикля:
      существительное, глагол, прилагательное и т.д.).

    Лимит MAX_TRANSLATIONS делится поровну между обрабатываемыми частями речи
    (запрошенными из списка либо всеми присутствующими при None), чтобы ни одна не
    вытесняла другую: для «set» без артикля видны и существительные, и глаголы, а для
    прилагательного «happy» — все его переводы. Дедуп — глобальный.
    """
    all_defs = data.get("def", [])

    if allowed_pos is None:
        # Все присутствующие части речи в порядке появления в статье.
        pos_order: list[str] = []
        for def_entry in all_defs:
            pos = def_entry.get("pos")
            if pos and pos not in pos_order:
                pos_order.append(pos)
    else:
        pos_order = list(allowed_pos)

    per_pos = max(1, MAX_TRANSLATIONS // max(1, len(pos_order)))
    result: list[str] = []
    seen: set[str] = set()

    def add_up_to(pos: str, limit: int) -> None:
        added = 0
        for def_entry in all_defs:
            if def_entry.get("pos") != pos:
                continue
            for tr in def_entry.get("tr", []):
                if added >= limit:
                    return
                candidates = [tr.get("text")] + [syn.get("text") for syn in tr.get("syn", [])]
                for cand in candidates:
                    if added >= limit:
                        return
                    if cand and cand not in seen:
                        seen.add(cand)
                        result.append(cand)
                        added += 1

    for pos in pos_order:
        add_up_to(pos, per_pos)
    return result


async def fetch_yandex_dictionary(
    session: aiohttp.ClientSession, word: str
) -> dict:
    """
    Словарный lookup слова в Yandex Dictionary.

    Возвращает «сырой» ответ (dict со статьёй) для последующей фильтрации через
    parse_dictionary; {} при отсутствии статьи (404/пусто) или ошибке сети — не
    критично, фолбэком послужит машинный перевод.
    """
    params = {"key": YANDEX_DICT_API_KEY, "lang": "en-ru", "text": word}
    try:
        async with session.get(YANDEX_DICT_URL, params=params) as resp:
            if resp.status == 404:
                return {}
            resp.raise_for_status()
            data = await resp.json()
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
        log.warning("Yandex Dictionary не сработал для %r: %s", word, exc)
        return {}

    return data or {}


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
