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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
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
        
        # Удаление вебхука (если был установлен)
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Webhook deleted")
        
    except Exception as e:
        logger.error(f"❌ Error on startup: {e}")
        raise


async def on_shutdown():
    """Действия при остановке бота"""
    try:
        await db.close_db()  # Если есть функция закрытия БД
        await bot.session.close()
        logger.info("✅ Bot stopped gracefully")
    except Exception as e:
        logger.error(f"❌ Error on shutdown: {e}")


async def main():
    """Основная функция"""
    try:
        # Подключение роутеров
        dp.include_router(user.router)
        dp.include_router(admin.router)
        logger.info("✅ Routers connected")
        
        # Startup
        await on_startup()
        
        # Запуск polling
        logger.info("🚀 Starting bot polling...")
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True
        )
        
    except Exception as e:
        logger.error(f"❌ Critical error: {e}")
    finally:
        await on_shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⚠️ Bot stopped by user")
    except Exception as e:
        logger.critical(f"💥 Fatal error: {e}")
        sys.exit(1)
