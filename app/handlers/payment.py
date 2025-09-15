from aiogram import Router, types
from aiogram.filters import Command
from app.services.database import db_service
from app.services.payment_service import PaymentService
from app.services.subscription_service import SubscriptionService
from app.services.user_service import UserService
from app.services.subscription_plan_service import SubscriptionPlanService
from app.models import User
from app.utils.decorators import error_handler
import logging
from yookassa import Configuration
from config.settings import settings

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("webhook"))
@error_handler
async def webhook_handler(message: types.Message):
    """Обработчик webhook от YooKassa (для тестирования)"""
    # В реальном приложении webhook должен приходить через HTTP POST
    # Этот хэндлер только для демонстрации
    await message.answer("Webhook handler - используется только для HTTP запросов")


async def process_yookassa_webhook(webhook_data: dict) -> bool:
    """Обработка webhook от YooKassa"""
    try:
        async with db_service.async_session() as session:
            success = await PaymentService.process_webhook(session, webhook_data)
            
            if success:
                # Если платеж успешен, создаем или продлеваем подписку
                event_type = webhook_data.get("event")
                payment_data = webhook_data.get("object")
                
                if event_type == "payment.succeeded" and payment_data:
                    payment_id = payment_data.get("id")
                    payment = await PaymentService.get_payment_by_yookassa_id(session, payment_id)
                    
                    if payment:
                        user = await session.get(User, payment.user_id)
                        if user:
                            # Проверяем, есть ли уже активная подписка
                            active_subscription = await SubscriptionService.get_active_subscription(
                                session, user.id
                            )
                            
                            if active_subscription:
                                # Продлеваем существующую подписку
                                await SubscriptionService.extend_subscription(
                                    session, active_subscription, 30
                                )
                            else:
                                # Получаем план подписки (по умолчанию месячный)
                                plan = await SubscriptionPlanService.get_monthly_plan(session)
                                if plan:
                                    # Создаем новую подписку
                                    await SubscriptionService.create_paid_subscription(
                                        session, user, plan, payment_id
                                    )
                            
                            logger.info(f"Subscription updated for user {user.telegram_id}")
                            return True
            
            return success
            
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return False


# Функция для настройки webhook в YooKassa (вызывается при запуске бота)
async def setup_yookassa_webhook():
    """Настройка webhook в YooKassa"""
    try:
        # Настраиваем конфигурацию YooKassa
        Configuration.account_id = settings.yookassa_shop_id
        Configuration.secret_key = settings.yookassa_secret_key
        
        if settings.webhook_url:
            webhook_url = f"{settings.webhook_url}/yookassa_webhook"
            
            logger.info(f"YooKassa webhook URL would be: {webhook_url}")
            logger.info("Note: Webhook setup should be done manually in YooKassa dashboard for production")
            
            # В продакшене webhook настраивается вручную через панель YooKassa
            # Здесь мы только логируем информацию
            return True
        else:
            logger.warning("Webhook URL not configured - running in polling mode")
            return True  # Не считаем это ошибкой для режима разработки
            
    except Exception as e:
        logger.error(f"Error setting up YooKassa webhook: {e}")
        return False