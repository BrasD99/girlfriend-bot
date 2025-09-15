import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from config.settings import settings
from app.services.database import db_service
from app.services.subscription_plan_service import SubscriptionPlanService
from app.handlers import (
    start_router,
    subscription_router,
    profile_router,
    profile_edit_router,
    conversation_router,
    payment_router
)
from app.handlers.payment import process_yookassa_webhook, setup_yookassa_webhook
import json

# Настройка логирования
logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=settings.bot_token)

# Настройка хранилища состояний
if settings.redis_url:
    try:
        storage = RedisStorage.from_url(settings.redis_url)
        logger.info("Using Redis storage for FSM")
    except Exception as e:
        logger.warning(f"Failed to connect to Redis: {e}. Using memory storage.")
        storage = MemoryStorage()
else:
    storage = MemoryStorage()
    logger.info("Using memory storage for FSM")

# Инициализация диспетчера
dp = Dispatcher(storage=storage)


async def on_startup():
    """Действия при запуске бота"""
    logger.info("Starting bot...")
    
    # Создаем таблицы в базе данных
    try:
        await db_service.create_tables()
        logger.info("Database tables created successfully")
        
        # Инициализируем планы подписок
        async with db_service.async_session() as session:
            await SubscriptionPlanService.initialize_plans_if_needed(session)
            logger.info("Subscription plans initialized")
            
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise
    
    # Настраиваем webhook для YooKassa
    try:
        await setup_yookassa_webhook()
    except Exception as e:
        logger.warning(f"Failed to setup YooKassa webhook: {e}")
    
    logger.info("Bot started successfully")


async def on_shutdown():
    """Действия при остановке бота"""
    logger.info("Shutting down bot...")
    
    # Закрываем соединение с базой данных
    await db_service.close()
    
    # Закрываем сессию бота
    await bot.session.close()
    
    logger.info("Bot shutdown complete")


async def yookassa_webhook_handler(request):
    """Обработчик webhook от YooKassa"""
    try:
        data = await request.json()
        logger.info(f"Received YooKassa webhook: {data}")
        
        success = await process_yookassa_webhook(data)
        
        if success:
            return web.Response(status=200, text="OK")
        else:
            return web.Response(status=400, text="Bad Request")
            
    except Exception as e:
        logger.error(f"Error processing YooKassa webhook: {e}")
        return web.Response(status=500, text="Internal Server Error")


def register_routers():
    """Регистрация роутеров"""
    dp.include_router(start_router)
    dp.include_router(subscription_router)
    dp.include_router(profile_router)
    dp.include_router(profile_edit_router)
    dp.include_router(conversation_router)
    dp.include_router(payment_router)


async def main():
    """Основная функция"""
    # Регистрируем роутеры
    register_routers()
    
    # Регистрируем события запуска и остановки
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    if settings.webhook_url:
        # Режим webhook
        logger.info("Starting bot in webhook mode")
        
        # Создаем веб-приложение
        app = web.Application()
        
        # Настраиваем webhook для Telegram
        webhook_requests_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot
        )
        webhook_requests_handler.register(app, path=settings.webhook_path)
        
        # Добавляем обработчик для YooKassa webhook
        app.router.add_post("/yookassa_webhook", yookassa_webhook_handler)
        
        # Настраиваем приложение
        setup_application(app, dp, bot=bot)
        
        # Устанавливаем webhook
        await bot.set_webhook(
            url=f"{settings.webhook_url}{settings.webhook_path}",
            drop_pending_updates=True
        )
        
        # Запускаем веб-сервер
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host="0.0.0.0", port=8000)
        await site.start()
        
        logger.info("Webhook server started on port 8000")
        
        # Ждем бесконечно
        try:
            await asyncio.Future()  # run forever
        finally:
            await runner.cleanup()
    else:
        # Режим polling
        logger.info("Starting bot in polling mode")
        
        # Удаляем webhook если он был установлен
        await bot.delete_webhook(drop_pending_updates=True)
        
        # Запускаем polling
        await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        raise