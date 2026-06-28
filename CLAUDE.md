# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Telegram bot (Russian-language UI) for learning English words **and phrases**. The user sends
an English word or phrase and the bot answers as a **plain-text table** (built with `|` and `-`),
with one copy button per row. Data sources (see `task.txt` for the spec, `PLAN.md` for the build log):

- **Yandex Cloud Translate** (`translate.api.cloud.yandex.net`) — translates single words *and* whole phrases/sentences.
- **Classic Yandex Dictionary** (`dictionary.yandex.net`) — for single words: translations grouped by part of speech (variants).
- **Free Dictionary API** (`dictionaryapi.dev`) — for single words: the English definition (значение) **and** an example sentence.

Answer shape depends on input (rendered as a 2-column `|`/`-` table; the header + dash row is always present):

```
# single word → up to 3 rows
| Часть    | Содержимое                      |
|----------|---------------------------------|
| Слово    | set (Set the tray there.)       |
| Перевод  | набор, комплект, множество      |
| Значение | To put (something) down, to rest. |

# phrase/sentence → 2 rows (no example, no definition)
| Часть   | Содержимое  |
|---------|-------------|
| Фраза   | good morning|
| Перевод | доброе утро |
```

Below the table the bot attaches one `CopyTextButton` per present row (📋 Слово + пример /
📋 Фраза / 📋 Перевод / 📋 Значение); each copies the row's value (right column), not the table markup.

Stack: Python 3.10+, aiogram 3.x, aiohttp.

## Commands

```bash
# Install (dev install pulls runtime deps too — but see note below)
pip install -r requirements.txt
pip install -r requirements-dev.txt   # pytest + pytest-asyncio

# Run the bot (reads BOT_TOKEN + Yandex keys from .env)
python main.py            # or: python -m bot.app

# Tests — pytest is configured in pytest.ini (asyncio_mode=auto, pythonpath=.)
pytest
pytest tests/test_api.py                                       # one file
pytest tests/test_formatting.py::TestBuildSections::test_word_full   # one test
```

Note: `requirements-dev.txt` only lists pytest packages, not `requirements.txt`. To run tests you must install both files (or `pip install -r requirements.txt -r requirements-dev.txt`).

Secrets come from `.env` (gitignored) via `python-dotenv`: `BOT_TOKEN`, `YANDEX_CLOUD_API_KEY`,
`YANDEX_FOLDER_ID`, `YANDEX_DICT_API_KEY`. `bot/app.py` exits with code 1 if **any** of these is
missing (verified at startup). How to obtain the Yandex keys is in `DEPLOYMENT.md` (§2.4.1).

## Architecture (package `bot/`)

Logic is split by concern across modules; understanding the flow requires reading several together:

- **`bot/config.py`** — env (`BOT_TOKEN`, the three Yandex keys), URL constants (`YANDEX_TRANSLATE_URL`, `YANDEX_DICT_URL`, `DICT_URL`), `API_TIMEOUT` = 10s, `START_TEXT`, `setup_logging()`.
- **`bot/api.py`** — `fetch_yandex_translate()` (POST to Cloud Translate), `fetch_yandex_dictionary()` + pure `parse_dictionary()` (translations by POS only), `fetch_free_definition()` + pure `pick_definition()` (definition + example).
- **`bot/formatting.py`** — `validate_input()`, `strip_leading_article()` (drops leading a/an/to), `build_sections(...)` → `list[(kind, text)]`, `sections_to_table()`.
- **`bot/keyboards.py`** — `SECTION_LABELS` + `build_copy_keyboard(sections)`.
- **`bot/handlers.py`** — `cmd_start()`, `handle_word()`, `register_handlers(dp)`.
- **`bot/app.py`** — `main()`: builds `Bot`/`Dispatcher`, registers handlers, owns the HTTP session, verifies secrets, runs polling.

Request flow in `handle_word()`: `validate_input` → `strip_leading_article` (head) → branch on `" " in head`:
- **word:** `gather(fetch_free_definition → (def, example), fetch_yandex_dictionary → variants)`; translation = comma-joined variants; if empty, fall back to `fetch_yandex_translate`.
- **phrase:** `fetch_yandex_translate` only (no example/definition).
- Then `build_sections(head, ...)` → `sections_to_table` + `build_copy_keyboard`. If there is no translation at all, reply «Не удалось перевести …».

### Non-obvious design decisions

- **Shared HTTP session via aiogram DI.** `app.main()` creates one `aiohttp.ClientSession` and stores it as `dp["http_session"]`; aiogram injects it into `handle_word` as the `http_session` kwarg. Do **not** create a session per request — reuse this one. The session and `bot.session` are closed in a `finally`.
- **No `parse_mode` is set on purpose.** Replies must be plain text (no Markdown) so parts copy cleanly.
- **Copy buttons use `CopyTextButton`, not callbacks.** Each button copies its text client-side — no callback round-trip, no button-press handler. `build_copy_keyboard` builds one button per section in its own row; needs `aiogram>=3.10.0` (Bot API 7.2). Buttons are a `reply_markup` and don't affect message text.
- **All external calls are best-effort.** Every `fetch_*` returns `None`/empty on network error, timeout, quota, 404, or malformed payload — nothing propagates as an exception. The handler simply omits a missing section and only errors out when there's no translation at all. This is why there is **no `WordNotFound` / no granular timeout/network messages** anymore (that was the pre-Yandex design).
- **Cloud Translate endpoint host is `translate.api.cloud.yandex.net`** (not `api.cloud.yandex.net`, which 404s). Auth is `Api-Key` header + `folderId` body; Yandex Dictionary uses a `key` query param (different key). All three are distinct secrets in `.env`.
- **Translations and the example come from different sources.** `parse_dictionary` collects `def[].tr[].text` + `def[].tr[].syn[].text` across all parts of speech, dedupes preserving order, caps at `MAX_TRANSLATIONS` (8). Yandex Dictionary returns **no** examples — the example and definition both come from Free Dictionary (`pick_definition` prefers a definition that also has an `example`).
- **Leading articles/particles are stripped.** `strip_leading_article` drops a single leading `a`/`an`/`to` when more text follows, so "to go"→"go", "a book"→"book" get full word treatment (variants + example + definition). A lone "to"/"a" and article-free phrases are unchanged.
- **Cloud Translate echoes the source text when it can't translate** (e.g. nonsense input); `fetch_yandex_translate` treats a result equal to the input (case-insensitive) as `None`, so such input yields «Не удалось перевести» instead of a fake "translation".
- **The answer is a plain-text table** (`sections_to_table` — `|`/`-`, header + dash row). `parse_mode` stays off so the pipes/dashes render literally; `build_copy_keyboard` copies each row's raw value, not the markup.
- **Handler registration order matters** — `cmd_start` (filtered on `CommandStart()`) is registered before the catch-all `handle_word`.
- **Input validation is strict:** Latin letters and spaces only (regex in `INPUT_RE`). Digits, punctuation, Cyrillic, and apostrophes (`don't`) are rejected — intentional per the spec, confirmed by tests.

### Language convention

User-facing strings and code comments are written in **Russian**. Match this when touching handlers, `config.py` texts, and docstrings.

## Testing approach

`tests/conftest.py` ships a minimal `FakeResponse`/`FakeSession` pair that mimics only the aiohttp surface actually used — both `session.get(url, params=...)` **and** `session.post(url, json=..., headers=...)`, plus `.status`/`.raise_for_status()`/`.json()` — so **no real network and no `aioresponses` dependency** is needed. `FakeSession.requests` records each call (`method`, `url`, `params`, `json`, `headers`) for assertions (e.g. that Translate sends the `Authorization: Api-Key …` header and a `folderId`).

- `asyncio_mode = auto` in `pytest.ini` — async test functions need no `@pytest.mark.asyncio` decorator.
- Handler tests mock the `Message` with `unittest.mock.AsyncMock` and patch API calls via `monkeypatch.setattr(bot.handlers, "fetch_…", …)` — patch the names *as imported in `bot.handlers`*. The test module imports `bot.handlers as h` and patches `h.fetch_*`.
- Pure parsers (`parse_dictionary` → list, `pick_definition` → (def, example)) and formatters (`validate_input`, `strip_leading_article`, `build_sections`, `sections_to_table`) are tested without any session.
- `tests/test_keyboards.py` asserts `build_copy_keyboard(sections)` yields one button per section, ordered, with `copy_text.text` matching each section's text and labels from `SECTION_LABELS`.

There are **no live Yandex credentials in CI/tests** — API calls are covered only by the mocked `FakeSession`. Live verification (real translation/definition) is a manual step for whoever has keys in `.env`.
