"""Middleware ограничений доступа к боту."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from .config import ACCESS_DENIED_TEXT, ALLOWED_USER_IDS


class AccessMiddleware(BaseMiddleware):
    """
    Ограничивает доступ к боту белым списком user_id (ALLOWED_USER_IDS).

    Пускает дальше, если: белый список пуст (доступ открыт всем) либо автор сообщения
    есть в списке. Иначе отвечает ACCESS_DENIED_TEXT и не вызывает хэндлер.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        if not ALLOWED_USER_IDS or (user is not None and user.id in ALLOWED_USER_IDS):
            return await handler(event, data)
        if isinstance(event, Message):
            await event.answer(ACCESS_DENIED_TEXT)
        # не вызываем handler — доступ закрыт
