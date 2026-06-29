# Развёртывание и настройка бота

Инструкция описывает полный путь: получение токена → локальный запуск → деплой на недорогом Linux VPS.

---

## 1. Получение токена через @BotFather

1. Откройте Telegram и найдите бота **[@BotFather](https://t.me/BotFather)**.
2. Отправьте команду `/newbot`.
3. Задайте **отображаемое имя** (например, `English Words Bot`).
4. Задайте **username** — должно оканчиваться на `bot` (например, `my_english_words_bot`).
5. BotFather пришлёт сообщение с **API токеном** вида:
   ```
   123456789:AAH...long-string...
   ```
6. Скопируйте токен целиком — он понадобится в файле `.env`.

> Полезные команды BotFather: `/setdescription` (описание бота), `/setabouttext` (о боте), `/token` (получить токен повторно). Никому не передавайте токен — при утечке перевыпустите его через `/revoke`.

---

## 2. Локальная настройка (Windows / Linux / macOS)

### 2.1. Установите Python 3.10+

Проверьте версию:
```bash
python --version      # Windows
python3 --version     # Linux / macOS
```
Нужен Python 3.10 или новее.

### 2.2. Создайте виртуальное окружение

**Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```
> Если исполнение скриптов заблокировано, разрешите на текущую сессию:
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

**Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

После активации в начале строки появится префикс `(venv)`.

### 2.3. Установите зависимости

```bash
pip install -r requirements.txt
```

### 2.4. Настройте `.env`

В корне проекта уже есть файл `.env` с плейсхолдерами. Откройте его и впишите свои значения:
```env
BOT_TOKEN=123456789:AAH...ваш-реальный-токен...

# Yandex Cloud Translate — перевод слов и фраз
YANDEX_CLOUD_API_KEY=ваш-ключ-Yandex-Cloud-Translate
YANDEX_FOLDER_ID=id-каталога-Yandex-Cloud

# Yandex Dictionary — переводы по частям речи для слов
YANDEX_DICT_API_KEY=ваш-ключ-Yandex-Dictionary
```
Без любого из этих значений бот не запустится (проверяется при старте).

#### 2.4.1. Получение ключей

**Yandex Cloud Translate** (`YANDEX_CLOUD_API_KEY`, `YANDEX_FOLDER_ID`):
1. Зарегистрируйтесь в [Yandex Cloud](https://cloud.yandex.ru/) и создайте платёжный аккаунт (есть бесплатный стартовый грант; для физлиц работает из РФ).
2. В консоли выберите каталог и скопируйте его **id** → это `YANDEX_FOLDER_ID`.
3. Создайте **сервисный аккаунт** в этом каталоге и выдайте ему роль `ai.translate.user` (исполнитель Translate).
4. Для сервисного аккаунта создайте **API-ключ** → это `YANDEX_CLOUD_API_KEY`.
Подробно: [документация Translate](https://cloud.yandex.ru/docs/translate/).

**Yandex Dictionary** (`YANDEX_DICT_API_KEY`):
1. Откройте [yandex.ru/dev/dictionary](https://yandex.ru/dev/dictionary) и нажмите «Получить ключ».
2. Зарегистрируйте приложение — получите бесплатный API-ключ (есть дневной лимит запросов).

### 2.5. Запуск бота локально

```bash
python main.py
```
В консоли появится `Бот запускается...`. Откройте своего бота в Telegram, нажмите **Start** (или отправьте `/start`) и пришлите любое английское слово, например `serendipity`.

Чтобы остановить бота — `Ctrl+C`.

---

## 3. Деплой на недорогом Linux VPS

Подойдёт любой VPS с 512 МБ RAM и Ubuntu/Debian (например, за $3–5/мес). Дальше — два варианта постоянного запуска: **systemd** (рекомендуется, автозапуск и перезапуск) или **tmux/screen** (проще, но без авто-восстановления).

### 3.0. Подготовка сервера

Зайдите на сервер по SSH и установите зависимости системы:
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
```

Загрузите код на сервер (через `git clone` или скопировав файлы), например в `/opt/english-bot`.

### 3.1. Вариант A — systemd (рекомендуется)

1. Создайте виртуальное окружение и установите зависимости:
   ```bash
   cd /opt/english-bot
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. Впишите токен в `.env` (как в п. 2.4).

3. Создайте файл службы:
   ```bash
   sudo nano /etc/systemd/system/english-bot.service
   ```
   Содержимое (поправьте `User` и пути под себя):
   ```ini
   [Unit]
   Description=English Words Telegram Bot
   After=network-online.target

   [Service]
   Type=simple
   User=root
   WorkingDirectory=/root/bot-for-english
   ExecStart=/root/bot-for-english/venv/bin/python /root/bot-for-english/main.py
   Restart=on-failure
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   ```

4. Запустите и включите автозапуск:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now english-bot
   ```

Управление:
```bash
sudo systemctl status english-bot     # статус
sudo systemctl restart english-bot    # перезапуск (после правок кода)
sudo journalctl -u english-bot -f     # просмотр логов в реальном времени
```

### 3.2. Вариант B — tmux / screen (быстрый запуск)

Удобно для теста или если не хочется возиться со службами. Процесс живёт, пока жива сессия.

**Подготовка (один раз):**
```bash
cd /opt/english-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# впишите токен в .env
```

**Через tmux:**л
```bash
tmux new -s english-bot
source venv/bin/activate
python main.py
# Отключиться, не убивая процесс: Ctrl+B, затем D
# Вернуться: tmux attach -t english-bot
```

**Через screen:**
```bash
screen -S english-bot
source venv/bin/activate
python main.py
# Отключиться: Ctrl+A, затем D
# Вернуться: screen -r english-bot
```

> Минус tmux/screen: при перезагрузке сервера бот не поднимется сам. Для постоянной работы prefer systemd.

---

## 4. Проверка после деплоя

1. В Telegram откройте бота, отправьте `/start` — должен прийти текст приветствия.
2. Отправьте слово `set` — придёт ответ из строк, разделённых `-----`: слово с примером, переводы (существительное и глагол через запятую), английское определение. Под ответом три кнопки: «📋 Слово + пример», «📋 Перевод», «📋 Значение» — тап копирует значение строки.
3. Отправьте фразу `good morning` или предложение `i love you` — придёт две строки (фраза / перевод), разделённые `-----`, и две кнопки; у фразы нет примера и значения.
4. Проверьте артикли как часть речи: `a book`/`an apple`/`the set` → только существительные переводы; `to book`/`to go` → только глагольные; `book` без артикля → и существительные, и глагольные.
5. Отправьте `123` (цифры) — отвергается; бессмысленное `asdfqwerty` → «Не удалось перевести …».
6. Логи на сервере: `sudo journalctl -u english-bot -f` (для systemd).

Готово — бот работает.
