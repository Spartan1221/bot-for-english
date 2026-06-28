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

## Дополнение 3: фиксы по результатам живой проверки

После подключения реальных ключей вскрылись проблемы: фразы не переводились (неверный hostname
Cloud Translate → 404), не было примеров (Yandex Dictionary не отдаёт `ex`), не распознавались
артикли. Источники перераспределены: **пример + определение — из Free Dictionary**, **переводы —
из Yandex Dictionary**, **фразы/предложения — из Cloud Translate**. Ответ оформлен таблицей.

- [x] 25. `config.py`: `YANDEX_TRANSLATE_URL` → `translate.api.cloud.yandex.net` (был `api.cloud.yandex.net` → 404).
- [x] 26. `api.py`: пример перенесён в Free Dictionary — `pick_definition`/`fetch_free_definition` возвращают `(definition, example)`; `parse_dictionary`/`fetch_yandex_dictionary` — только переводы.
- [x] 27. `api.py`: `fetch_yandex_translate` отбрасывает ответ, равный исходному тексту (Cloud отдаёт его as-is для непереводимого).
- [x] 28. `formatting.py`: `strip_leading_article` (a/an/to) + `sections_to_table` (таблица через `-` и `|`) вместо `sections_to_text`.
- [x] 29. `handlers.py`: отброс ведущего артикля, `gather(free_definition, dictionary)`, вывод таблицей.
- [x] 30. Тесты обновлены; живая проверка реальными API (слово/фраза/предложение/артикли/непереводимое) — ок, 59 тестов зелёные.

## Дополнение 4: Microsoft Translator + артикли как части речи + разделитель вместо таблицы

Табличный формат убран — секции теперь разделены строкой `-----`. Переводчик заменён:
вместо **Yandex Cloud Translate** — **Microsoft (Azure) Translator**. Артикли стали указанием
части речи: **a/an/the → существительное**, **to → глагол**, **без артикля → и существительное,
и глагол** (плоско через запятую). Yandex Dictionary и Free Dictionary остались.

- [x] 31. `config.py`: убрать `YANDEX_CLOUD_API_KEY`/`YANDEX_FOLDER_ID`/`YANDEX_TRANSLATE_URL`; добавить `AZURE_TRANSLATOR_KEY`/`AZURE_TRANSLATOR_REGION`/`AZURE_TRANSLATE_URL`.
- [x] 32. `api.py`: `fetch_microsoft_translate` (POST Azure, заголовки `Ocp-Apim-Subscription-Key`/`-Region`, guard от echo); `parse_dictionary(data, allowed_pos)` с фильтром по частям речи; `fetch_yandex_dictionary(session, word, allowed_pos)`.
- [x] 33. `formatting.py`: `classify_input` (a/an/the→noun, to→verb, без артикля→noun+verb, иначе фраза) вместо `strip_leading_article`; `sections_to_text` (разделитель `-----`) вместо `sections_to_table`.
- [x] 34. `handlers.py`: классификация → поток (слово с фильтром POS / фраза), Azure-перевод.
- [x] 35. `app.py` + `.env`: секреты Azure (`AZURE_TRANSLATOR_KEY`/`AZURE_TRANSLATOR_REGION`) + `YANDEX_DICT_API_KEY`.
- [x] 36. Фикс баланса частей речи: лимит переводов делится поровну между запрошенными POS, чтобы noun и verb не вытесняли друг друга.
- [x] 37. Тесты переписаны; живая проверка (слово/артикли a-an-the-to/фраза/предложение) — ок, 63 теста зелёные.

## Итоговая архитектура (пакет `bot/`)

Логика разбита по модулям по функциональному признаку:

| Модуль | Ответственность |
|---|---|
| `main.py` (корень) | Тонкая точка входа: `asyncio.run(bot.app.main())`. |
| `bot/config.py` | `BOT_TOKEN`, ключи Azure Translator и Yandex Dictionary из `.env`, константы URL, таймаут, `START_TEXT`, `setup_logging()`. |
| `bot/api.py` | `fetch_microsoft_translate()` (Azure), `fetch_yandex_dictionary()` + `parse_dictionary(allowed_pos)` (переводы по частям речи), `fetch_free_definition()` + `pick_definition()` (определение + пример). |
| `bot/formatting.py` | `validate_input()`, `classify_input()` (артикль → часть речи), `build_sections()`, `sections_to_text()` (разделитель `-----`). |
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
