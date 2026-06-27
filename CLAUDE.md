# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Telegram bot (Russian-language UI) for learning English words. A user sends an English word or phrase; the bot queries the Dictionary API (`dictionaryapi.dev`) for a definition + example and MyMemory for a Russian translation, then replies with a **strictly two-line plain-text answer**:

```
serendipity (Finding a beautiful old book in a dusty attic is pure serendipity.)
счастливая случайность (the occurrence and development of events by chance ...)
```

Below the text the bot attaches two inline **copy buttons** — one copies line 1, the other line 2 — so the user can copy each half without manual selection.

Stack: Python 3.10+, aiogram 3.x, aiohttp. Source of truth for the product spec is `task.txt`; the step-by-step build log is `PLAN.md`.

## Commands

```bash
# Install (dev install pulls runtime deps too — but see note below)
pip install -r requirements.txt
pip install -r requirements-dev.txt   # pytest + pytest-asyncio

# Run the bot (reads BOT_TOKEN from .env)
python main.py            # or: python -m bot.app

# Tests — pytest is configured in pytest.ini (asyncio_mode=auto, pythonpath=.)
pytest
pytest tests/test_api.py                              # one file
pytest tests/test_formatting.py::TestFormatAnswer::test_full_answer   # one test
```

Note: `requirements-dev.txt` only lists pytest packages, not `requirements.txt`. To run tests you must install both files (or `pip install -r requirements.txt -r requirements-dev.txt`).

`BOT_TOKEN` comes from `.env` (gitignored) via `python-dotenv`; `bot/app.py` exits with code 1 if it is missing. Deployment is documented in `DEPLOYMENT.md`.

## Architecture (package `bot/`)

Logic is split by concern across modules; understanding the flow requires reading several together:

- **`bot/config.py`** — env (`BOT_TOKEN`), constants (`DICT_URL`, `TRANSLATE_URL`, `API_TIMEOUT` = 10s), `START_TEXT`, `setup_logging()`.
- **`bot/api.py`** — `fetch_definition()` (Dictionary API), `fetch_translation()` (MyMemory), pure `pick_definition()`, and the `WordNotFound` exception.
- **`bot/formatting.py`** — `validate_input()`, `format_answer()`, and `format_answer_parts()` (all pure). `format_answer_parts` returns the two lines as a tuple so the handler can bind them to copy buttons; `format_answer` joins them.
- **`bot/keyboards.py`** — `build_copy_keyboard(line1, line2)` builds the inline copy buttons.
- **`bot/handlers.py`** — `cmd_start()`, `handle_word()`, `register_handlers(dp)`.
- **`bot/app.py`** — `main()`: builds `Bot`/`Dispatcher`, registers handlers, owns the HTTP session, runs polling.

Request flow in `handle_word()`: validate → lowercase for the API query → run both API calls in parallel with `asyncio.gather` → format → answer.

### Non-obvious design decisions

- **Shared HTTP session via aiogram DI.** `app.main()` creates one `aiohttp.ClientSession` and stores it as `dp["http_session"]`; aiogram then injects it into `handle_word` as the `http_session` kwarg. Do **not** create a session per request — reuse this one. The session and `bot.session` are closed in a `finally`.
- **No `parse_mode` is set on purpose.** Replies must be plain text (no Markdown) so users can copy parts cleanly. Keep `format_answer()` output Markdown-free.
- **Copy buttons use `CopyTextButton`, not callbacks.** Each button copies its text straight to the clipboard client-side — there is no callback round-trip and no handler for button presses. `build_copy_keyboard` puts one button per row (two rows) for the two answer lines; it needs `aiogram>=3.10.0` (Bot API 7.2). The buttons are a `reply_markup` on the same plain-text answer; they do not affect the message text.
- **`fetch_definition` raises; `fetch_translation` is best-effort.** Definition lookup raises `WordNotFound` on HTTP 404 / empty payload, and propagates `aiohttp.ClientError` / `asyncio.TimeoutError` to the handler (which maps each to a user-facing message). Translation *never* throws — it returns `None` on any error, quota/empty result, or `MYMEMORY WARNING` text, so a missing translation degrades gracefully (shown as "перевод недоступен").
- **`pick_definition` prefers entries that have an example**, falling back to the first definition with text if none has one.
- **Handler registration order matters** — `cmd_start` (filtered on `CommandStart()`) is registered before the catch-all `handle_word` in `register_handlers()`.
- **Input validation is strict:** Latin letters and spaces only (regex in `INPUT_RE`). Digits, punctuation, Cyrillic, and apostrophes (`don't`) are rejected — this is intentional per the spec, confirmed by tests.

### Language convention

User-facing strings and code comments are written in **Russian**. Match this when touching handlers, `config.py` texts, and docstrings.

## Testing approach

`tests/conftest.py` ships a minimal `FakeResponse`/`FakeSession` pair that mimics only the aiohttp surface actually used (`async with session.get(url, params=...) as resp` + `.status`/`.raise_for_status()`/`.json()`), so **no real network and no `aioresponses` dependency** is needed. Use the `make_response` and `fake_session_factory` fixtures for API-layer tests.

- `asyncio_mode = auto` in `pytest.ini` — async test functions need no `@pytest.mark.asyncio` decorator.
- Handler tests mock the `Message` with `unittest.mock.AsyncMock` and patch API calls via `monkeypatch.setattr("bot.handlers.fetch_definition", ...)` — patch the name *as imported in `bot.handlers`*, not the original definition site.
- `format_answer`/`validate_input` tests encode the exact two-line contract (including a test that reproduces the canonical example from `task.txt`); keep new formatting behavior consistent with `test_exactly_two_lines`.
- `tests/test_keyboards.py` checks `build_copy_keyboard` returns two single-button rows whose `copy_text.text` match the two answer lines. Handler tests (`test_handle_word_sends_copy_keyboard`) assert the markup is attached to the answer.
