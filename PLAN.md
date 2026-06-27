# План разработки Telegram-бота для английских слов

Бот принимает английское слово или фразу и возвращает ответ из двух строк:

```
word (пример использования)
перевод (определение на английском)
```

Источники данных: Dictionary API (`dictionaryapi.dev`) для определения и примера,
MyMemory API для перевода на русский. Стек: Python 3.10+, aiogram 3.x, aiohttp.

## Шаги

- [x] 1. Описать архитектуру: конфигурация → валидация → запросы к API → форматирование → хэндлеры.
- [x] 2. Настроить загрузку токена из `.env` через `python-dotenv`.
- [x] 3. Реализовать валидацию ввода (только латинские буквы и пробелы; одиночные слова и фразы).
- [x] 4. Реализовать асинхронный запрос к Dictionary API: определение + пример использования.
- [x] 5. Реализовать асинхронный запрос к MyMemory API: перевод слова на русский.
- [x] 6. Запускать оба запроса параллельно через `asyncio.gather`.
- [x] 7. Реализовать функцию форматирования ответа: ровно две строки, обычный текст без Markdown.
- [x] 8. Добавить команду `/start` с приветствием и инструкцией.
- [x] 9. Добавить обработку ошибок: таймауты, ошибки сети, слово не найдено, некорректный ввод.
- [x] 10. Настроить общий `aiohttp.ClientSession` с таймаутом (переиспользование соединений).
- [x] 11. Подготовить `requirements.txt` и `.env` (плейсхолдер токена).
- [x] 12. Написать `DEPLOYMENT.md`: BotFather, локальный запуск, деплой на Linux VPS.
- [x] 13. Разбить `main.py` на модули по функциональному признаку (пакет `bot/`: config, api, formatting, handlers, app).
- [x] 14. Добавить unit-тесты (`pytest` + `pytest-asyncio`): валидация, форматирование, API-слой, хэндлеры.

## Итоговая архитектура (пакет `bot/`)

Логика разбита по модулям по функциональному признаку:

| Модуль | Ответственность |
|---|---|
| `main.py` (корень) | Тонкая точка входа: `asyncio.run(bot.app.main())`. |
| `bot/config.py` | `BOT_TOKEN` из `.env`, константы URL, таймаут, `START_TEXT`, `setup_logging()`. |
| `bot/api.py` | `fetch_definition()` (Dictionary API), `fetch_translation()` (MyMemory), `pick_definition()`, `WordNotFound`. |
| `bot/formatting.py` | `validate_input()` и `format_answer()`. |
| `bot/handlers.py` | `cmd_start()` для `/start`, `handle_word()` для остальных сообщений, `register_handlers(dp)`. |
| `bot/app.py` | `main()`: создаёт бота, диспетчер, общий HTTP-сеанс и запускает long-polling. |

Тесты (`pytest`, `pytest-asyncio`, режим `asyncio_mode = auto`):

| Файл | Что покрывает |
|---|---|
| `tests/test_formatting.py` | `validate_input`, `format_answer` (чистые функции). |
| `tests/test_api.py` | `pick_definition` и `fetch_*` через фейковую aiohttp-сессию. |
| `tests/test_handlers.py` | `cmd_start`, `handle_word` (message и API мокируются). |
| `tests/conftest.py` | Общие фикстуры `make_response`, `fake_session_factory` (без похода в сеть). |
