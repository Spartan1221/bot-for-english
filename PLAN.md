# План разработки Telegram-бота для английских слов

Бот принимает английское слово или фразу и возвращает ответ из двух строк:

```
word (пример использования)
перевод (определение на английском)
```

Источники данных: **Yandex Cloud Translate** (перевод слов и фраз) + **классический
Yandex Dictionary** (переводы по частям речи и примеры для отдельных слов) + **Free Dictionary
API** (`dictionaryapi.dev`, английское определение). Стек: Python 3.10+, aiogram 3.x, aiohttp.

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

## Дополнение: кнопки для копирования ответа

Под ответом из двух строк добавлены две inline-кнопки: одна копирует первую строку
(слово с примером), другая — вторую (значение с переводом). Кнопки используют
`CopyTextButton` (Telegram Bot API 7.2) и копируют текст прямо в буфер обмена, без
callback к боту.

- [x] 15. Вынести сборку строк ответа в `format_answer_parts()` (`bot/formatting.py`), `format_answer()` делегирует ей.
- [x] 16. Добавить модуль `bot/keyboards.py` с `build_copy_keyboard(line1, line2)` — две кнопки `CopyTextButton` в две строки.
- [x] 17. В `handle_word` прикреплять клавиатуру к ответу; покрыть изменения тестами (`tests/test_keyboards.py`, расширить `test_formatting.py` и `test_handlers.py`).

## Дополнение 2: переход на Yandex API + новый шаблон ответа

Старая связка (MyMemory + Free Dictionary) не переводила фразы и не различала части речи.
Перешли на: **Yandex Cloud Translate** (перевод слов и предложений) + **классический Yandex
Dictionary** (переводы по частям речи + пример для отдельных слов) + **Free Dictionary API**
(английское определение). Шаблон ответа стал секционным: **слово → 3 секции** (слово+пример /
перевод / значение), **фраза → 2 секции** (фраза / перевод, без значения); переводы — одним списком
через запятую; каждой присутствующей секции — своя кнопка копирования.

- [x] 18. `config.py`: env `YANDEX_CLOUD_API_KEY`/`YANDEX_FOLDER_ID`/`YANDEX_DICT_API_KEY` и URL Yandex; убрать MyMemory.
- [x] 19. `api.py`: `fetch_yandex_translate` (POST Cloud Translate), `parse_dictionary` (чистая) + `fetch_yandex_dictionary`, `fetch_free_definition` + `pick_definition`; все вызовы best-effort; убрать `WordNotFound`/старые `fetch_*`.
- [x] 20. `formatting.py`: `build_sections(...)` → список `(kind, text)` + `sections_to_text`; ветвление слово/фраза.
- [x] 21. `keyboards.py`: обобщить `build_copy_keyboard(sections)` + `SECTION_LABELS`.
- [x] 22. `handlers.py`: поток слово/фраза (`" " in query`), `gather(dictionary, free_definition)`, фолбэк переводом, секции+клавиатура, ошибка «не удалось перевести».
- [x] 23. `app.py`: проверка `BOT_TOKEN` + трёх Yandex-секретов при старте (`sys.exit(1)` если чего-то нет).
- [x] 24. Переписать тесты под новый API/шаблон (`conftest` — `post()` у `FakeSession`; `test_api`/`test_formatting`/`test_keyboards`/`test_handlers`).

## Итоговая архитектура (пакет `bot/`)

Логика разбита по модулям по функциональному признаку:

| Модуль | Ответственность |
|---|---|
| `main.py` (корень) | Тонкая точка входа: `asyncio.run(bot.app.main())`. |
| `bot/config.py` | `BOT_TOKEN` и ключи Yandex из `.env`, константы URL (Translate/Dictionary/Free Dictionary), таймаут, `START_TEXT`, `setup_logging()`. |
| `bot/api.py` | `fetch_yandex_translate()` (Cloud Translate), `fetch_yandex_dictionary()` + `parse_dictionary()` (словарь/части речи/пример), `fetch_free_definition()` + `pick_definition()` (определение). |
| `bot/formatting.py` | `validate_input()`, `build_sections()` (секции `(kind, text)`), `sections_to_text()`. |
| `bot/keyboards.py` | `build_copy_keyboard(sections)` + `SECTION_LABELS` — кнопка `CopyTextButton` на каждую секцию. |
| `bot/handlers.py` | `cmd_start()` для `/start`, `handle_word()` (ветвление слово/фраза → секции + клавиатура), `register_handlers(dp)`. |
| `bot/app.py` | `main()`: создаёт бота, диспетчер, общий HTTP-сеанс; проверяет секреты; запускает long-polling. |

Тесты (`pytest`, `pytest-asyncio`, режим `asyncio_mode = auto`):

| Файл | Что покрывает |
|---|---|
| `tests/test_formatting.py` | `validate_input`, `build_sections` (слово/фраза/пропуски), `sections_to_text`. |
| `tests/test_keyboards.py` | `build_copy_keyboard(sections)`: подписки по `SECTION_LABELS`, цели копирования, порядок. |
| `tests/test_api.py` | `parse_dictionary`/`pick_definition` (чистые) и `fetch_*` (translate POST, dictionary/free-def GET) через фейковую сессию. |
| `tests/test_handlers.py` | `cmd_start`, `handle_word`: пути слова/фразы, фолбэк переводом, ошибка «не удалось перевести». |
| `tests/conftest.py` | `FakeResponse`, `FakeSession` (GET + POST), фикстуры `make_response`, `fake_session_factory` (без похода в сеть). |
