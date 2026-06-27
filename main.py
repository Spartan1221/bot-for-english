"""
Точка входа бота. Логика разбита по модулям пакета `bot/`:

    bot/config.py     — переменные окружения, константы, тексты, логирование;
    bot/api.py        — запросы к Dictionary API и MyMemory;
    bot/formatting.py — валидация ввода и форматирование ответа;
    bot/handlers.py   — хэндлеры aiogram;
    bot/app.py        — сборка бота и запуск polling.

Запуск: `python main.py` (или `python -m bot.app`).
"""

from __future__ import annotations

import asyncio
import logging

from bot.app import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.getLogger("english-bot").info("Бот остановлен")
