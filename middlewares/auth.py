from typing import Any, Awaitable, Callable, Dict, Union
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from config import config
from database import db

Event = Union[Message, CallbackQuery]


class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Event, Dict[str, Any]], Awaitable[Any]],
        event: Event,
        data: Dict[str, Any],
    ) -> Any:
        tg_user = getattr(event, "from_user", None)
        if tg_user is None:
            return

        user_id = tg_user.id
        if user_id not in config.ALLOWED_USERS:
            if isinstance(event, CallbackQuery):
                await event.answer("⛔ Доступ запрещён.", show_alert=True)
            else:
                await event.answer("⛔ Доступ запрещён.")
            return

        user = await db.get_user(user_id)
        if user is None:
            await db.create_user(user_id, tg_user.username or "unknown")
            user = await db.get_user(user_id)

        if user["is_blocked"]:
            if isinstance(event, CallbackQuery):
                await event.answer("🚫 Вы заблокированы администратором.", show_alert=True)
            else:
                await event.answer("🚫 Вы заблокированы администратором.")
            return

        data["user_id"] = user_id
        data["is_admin"] = (user_id == config.ADMIN_ID)
        return await handler(event, data)
