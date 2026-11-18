import asyncio
import logging
import os

from aiohttp import web
from aiogram import Bot, Dispatcher

from config import config
from database import db
from middlewares.auth import AuthMiddleware
from handlers import user, admin, files

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def start_health_server():
    """Amvera ждёт, что сервис слушает containerPort. Поднимаем / и /health."""
    port = int(os.getenv("PORT", "80"))

    async def ok(_request):
        return web.Response(text="ok")

    app = web.Application()
    app.router.add_get("/", ok)
    app.router.add_get("/health", ok)

    runner = web.AppRunner(app)
    await runner.setup()
    try:
        await web.TCPSite(runner, "0.0.0.0", port).start()
        logger.info("Health server on port %s", port)
    except OSError as e:
        logger.warning("Не смог занять порт %s (%s) — бот всё равно запускается", port, e)
    return runner


async def main():
    if not config.BOT_TOKEN:
        raise SystemExit(
            "BOT_TOKEN пуст. Задай переменную окружения BOT_TOKEN "
            "(в Amvera — Environment variables)."
        )
    if not config.API_KEY:
        logger.warning("API_KEY пуст — запросы к ИИ будут падать, пока не задашь ключ.")

    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    dp.include_router(user.router)
    dp.include_router(admin.router)
    dp.include_router(files.router)

    runner = await start_health_server()
    try:
        await db.init()
        logger.info("DB ready. Starting bot...")
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
