# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Telegram bot (Russian-language UI) for learning English words **and phrases**. The user sends
an English word or phrase and the bot answers as **plain text whose sections are separated by `-----`**,
with one copy button per section. Data sources (see `task.txt` for the spec, `PLAN.md` for the log):

- **Yandex Cloud Translate** (`translate.api.cloud.yandex.net`) — translates single words *and* whole phrases/sentences.
- **Classic Yandex Dictionary** (`dictionary.yandex.net`) — for single words: translations **filtered by part of speech**.
- **Free Dictionary API** (`dictionaryapi.dev`) — for single words: the English definition (значение) **and** an example sentence.

An **article selects the part of speech** for a word lookup:
- `a` / `an` / `the` + word → noun translations only.
- `to` + word → verb translations only.
- word with no article → noun **and** verb translations (flat, comma-separated).

Answer shape (sections separated by `-----`; only present sections appear):
```
# single word → up to 3 sections
set (Set the tray there.)
-----
набор, комплект, установка, ставить, установить
-----
To put (something) down, to rest.

# phrase/sentence → 2 sections
good morning
-----
доброе утро
```

Below the text the bot attaches one `CopyTextButton` per section (📋 Слово + пример /
📋 Фраза / 📋 Перевод / 📋 Значение); each copies that section's text.

Stack: Python 3.10+, aiogram 3.x, aiohttp.

## Commands

```bash
# Install (dev install pulls runtime deps too — but see note below)
pip install -r requirements.txt
pip install -r requirements-dev.txt   # pytest + pytest-asyncio

# Run the bot (reads BOT_TOKEN + API keys from .env)
python main.py            # or: python -m bot.app

# Tests — pytest is configured in pytest.ini (asyncio_mode=auto, pythonpath=.)
pytest
pytest tests/test_api.py::TestParseDictionary::test_noun_only   # one test
```

Note: `requirements-dev.txt` only lists pytest packages, not `requirements.txt`. To run tests you must install both files (or `pip install -r requirements.txt -r requirements-dev.txt`).

Secrets come from `.env` (gitignored) via `python-dotenv`: `BOT_TOKEN`, `YANDEX_CLOUD_API_KEY`,
`YANDEX_FOLDER_ID`, `YANDEX_DICT_API_KEY`. `bot/app.py` exits with code 1 if **any** of these
is missing (verified at startup). How to obtain the keys is in `DEPLOYMENT.md` (§2.4.1).

## Architecture (package `bot/`)

Logic is split by concern across modules; understanding the flow requires reading several together:

- **`bot/config.py`** — env (`BOT_TOKEN`, Yandex Cloud Translate + Yandex Dictionary keys), URL constants (`YANDEX_TRANSLATE_URL`, `YANDEX_DICT_URL`, `DICT_URL`), `API_TIMEOUT` = 10s, `START_TEXT`, `setup_logging()`.
- **`bot/api.py`** — `fetch_yandex_translate()` (POST to Yandex Cloud Translate), `fetch_yandex_dictionary()` + pure `parse_dictionary(allowed_pos)` (translations filtered by POS), `fetch_free_definition()` + pure `pick_definition()` (definition + example).
- **`bot/formatting.py`** — `validate_input()`, `classify_input()` (article → part of speech / phrase), `build_sections(...)` → `list[(kind, text)]`, `sections_to_text()` (joins sections with `-----`).
- **`bot/keyboards.py`** — `SECTION_LABELS` + `build_copy_keyboard(sections)`.
- **`bot/handlers.py`** — `cmd_start()`, `handle_word()`, `register_handlers(dp)`.
- **`bot/app.py`** — `main()`: builds `Bot`/`Dispatcher`, registers handlers, owns the HTTP session, verifies secrets, runs polling.

Request flow in `handle_word()`: `validate_input` → `classify_input` (returns `head`, `allowed_pos`, `is_phrase`) → branch:
- **word:** `gather(fetch_free_definition → (def, example), fetch_yandex_dictionary(head, allowed_pos) → variants)`; translation = comma-joined variants; if empty, fall back to `fetch_yandex_translate`.
- **phrase:** `fetch_yandex_translate` only (no example/definition).
- Then `build_sections(head, ...)` → `sections_to_text` + `build_copy_keyboard`. If there is no translation at all, reply «Не удалось перевести …».

### Non-obvious design decisions

- **Shared HTTP session via aiogram DI.** `app.main()` creates one `aiohttp.ClientSession` and stores it as `dp["http_session"]`; aiogram injects it into `handle_word` as the `http_session` kwarg. Do **not** create a session per request — reuse this one. The session and `bot.session` are closed in a `finally`.
- **No `parse_mode` is set on purpose.** Replies must be plain text (no Markdown) so parts copy cleanly. The `-----` separator and section text are literal characters.
- **Copy buttons use `CopyTextButton`, not callbacks.** Each button copies its text client-side — no callback round-trip, no button-press handler. One button per section; needs `aiogram>=3.10.0` (Bot API 7.2).
- **All external calls are best-effort.** Every `fetch_*` returns `None`/empty on network error, timeout, quota, 404, or malformed payload — nothing propagates as an exception. The handler omits a missing section and only errors out when there is no translation at all. This is why there is **no `WordNotFound` / no granular timeout/network messages**.
- **Yandex Cloud Translate auth:** header `Authorization: Api-Key <key>`, body `{folderId, texts, sourceLanguageCode, targetLanguageCode}`, response `{translations:[{text}]}`. The host must be `translate.api.cloud.yandex.net` (not `api.cloud.yandex.net`, which 404s). It can echo untranslatable input verbatim, so `fetch_yandex_translate` treats a result equal to the input (case-insensitive) as `None`.
- **Articles select the part of speech** (`classify_input`): `a`/`an`/`the` → noun, `to` → verb, no article → noun+verb. Only a leading article followed by a single word triggers this (`to go` → verb "go"); a lone article or a longer phrase is treated as a phrase/sentence and machine-translated.
- **`parse_dictionary` balances the cap across requested parts of speech** (`MAX_TRANSLATIONS` // `len(allowed_pos)` each), so when both noun and verb are requested neither crowds out the other. Order is noun-first then verb; dedup is global.
- **Translations and the example come from different sources.** Yandex Dictionary returns **no** examples — the example and definition both come from Free Dictionary (`pick_definition` prefers a definition that also has an `example`).
- **Handler registration order matters** — `cmd_start` (filtered on `CommandStart()`) is registered before the catch-all `handle_word`.
- **Input validation is strict:** Latin letters and spaces only (regex in `INPUT_RE`). Digits, punctuation, Cyrillic, and apostrophes (`don't`) are rejected — intentional per the spec, confirmed by tests.

### Language convention

User-facing strings and code comments are written in **Russian**. Match this when touching handlers, `config.py` texts, and docstrings.

## Testing approach

`tests/conftest.py` ships a minimal `FakeResponse`/`FakeSession` pair that mimics only the aiohttp surface actually used — both `session.get(url, params=...)` and `session.post(url, json=..., headers=...)`, plus `.status`/`.raise_for_status()`/`.json()` — so **no real network and no `aioresponses` dependency** is needed. `FakeSession.requests` records each call (`method`, `url`, `params`, `json`, `headers`) for assertions.

- `asyncio_mode = auto` in `pytest.ini` — async test functions need no `@pytest.mark.asyncio` decorator.
- Handler tests mock the `Message` with `unittest.mock.AsyncMock` and patch API calls via `monkeypatch.setattr(bot.handlers, "fetch_…", …)` — patch the names *as imported in `bot.handlers`*. The test module imports `bot.handlers as h` and patches `h.fetch_*`.
- Pure parsers (`parse_dictionary(allowed_pos)` → list, `pick_definition` → (def, example)) and formatters (`validate_input`, `classify_input`, `build_sections`, `sections_to_text`) are tested without any session.
- `tests/test_keyboards.py` asserts `build_copy_keyboard(sections)` yields one button per section, ordered, with `copy_text.text` matching each section's text.

There are **no live API credentials in CI/tests** — API calls are covered only by the mocked `FakeSession`. Live verification (real translation/definition) is a manual step for whoever has keys in `.env`.
