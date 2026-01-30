import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher, executor
from aiogram.types import ParseMode
from aiogram.contrib.fsm_storage.memory import MemoryStorage

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
bot = Bot(token=config.BOT_TOKEN, parse_mode=ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


async def on_startup(dispatcher):
    """Действия при запуске бота"""
    try:
        await db.init_db()
        logger.info("✅ Database initialized")
        logger.info("🚀 Bot started successfully")
    except Exception as e:
        logger.error(f"❌ Error on startup: {e}")


async def on_shutdown(dispatcher):
    """Действия при остановке бота"""
    try:
        await bot.close()
        logger.info("✅ Bot stopped")
    except Exception as e:
        logger.error(f"❌ Error on shutdown: {e}")


if __name__ == "__main__":
    # Регистрация хендлеров
    from handlers import user, admin
    user.register_handlers(dp)
    admin.register_handlers(dp)
    
    logger.info("✅ Handlers registered")
    
    # Запуск
    executor.start_polling(
        dp,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True
    )
