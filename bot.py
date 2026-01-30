import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import config
import database as db
from handlers import user, admin

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Бот и диспетчер
bot = Bot(
    token=config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()


async def on_startup():
    """Действия при запуске бота"""
    try:
        await db.init_db()
        logger.info("✅ Database initialized")
        logger.info("🚀 Bot started successfully")
    except Exception as e:
        logger.error(f"❌ Error on startup: {e}")


async def on_shutdown():
    """Действия при остановке бота"""
    try:
        await bot.session.close()
        logger.info("✅ Bot stopped")
    except Exception as e:
        logger.error(f"❌ Error on shutdown: {e}")


async def main():
    # Регистрация роутеров
    dp.include_router(user.router)
    dp.include_router(admin.router)
    
    logger.info("✅ Handlers registered")
    
    # Запуск
    await on_startup()
    try:
        await dp.start_polling(bot, skip_updates=True)
    finally:
        await on_shutdown()


if __name__ == "__main__":
    asyncio.run(main())
