from aiogram import Router, types
from aiogram.filters import Command
from app.services.database import db_service
from app.services.payment_service import PaymentService
from app.services.subscription_service import SubscriptionService
from app.services.user_service import UserService
from app.services.subscription_plan_service import SubscriptionPlanService
from app.models import User
from app.utils.decorators import error_handler
from app.utils.helpers import format_datetime_for_user
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
                            # Получаем план из метаданных платежа или используем месячный по умолчанию
                            metadata = payment_data.get("metadata", {})
                            plan_id = metadata.get("plan_id")
                            
                            plan = None
                            if plan_id:
                                plan = await SubscriptionPlanService.get_plan_by_id(session, int(plan_id))
                            
                            if not plan:
                                # Используем месячный план по умолчанию
                                plan = await SubscriptionPlanService.get_plan_by_type(session, "monthly")
                            
                            if plan:
                                # Создаем подписку
                                subscription = await SubscriptionService.create_paid_subscription(
                                    session, user, plan, payment_id
                                )
                                
                                # Отправляем уведомление пользователю
                                await _notify_user_subscription_activated(user, plan, subscription)
                                
                                logger.info(f"Subscription activated for user {user.telegram_id} with plan {plan.name}")
                                return True
                            else:
                                logger.error(f"No plan found for payment {payment_id}")
            
            return success
            
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return False


async def _notify_user_subscription_activated(user: User, plan, subscription):
    """Уведомление пользователя об активации подписки"""
    try:
        from main import bot
        from app.utils.keyboards import get_subscription_keyboard
        
        success_text = (
            "🎉 **Оплата прошла успешно!**\n\n"
            f"✅ Подписка '{plan.name}' активирована\n"
            f"📅 Действует до: {format_datetime_for_user(subscription.end_date, include_time=True)}\n"
            "💬 Все функции бота доступны\n\n"
            "Спасибо за покупку! 💕\n\n"
            "Теперь вы можете:\n"
            "• Создать профиль девушки\n"
            "• Начать общение\n"
            "• Использовать все возможности бота"
        )
        
        # Получаем информацию о подписке для корректного отображения клавиатуры
        async with db_service.async_session() as session:
            subscription_info = await SubscriptionService.get_subscription_info(session, user.id)
        
        keyboard = get_subscription_keyboard(subscription_info)
        
        await bot.send_message(
            chat_id=user.telegram_id,
            text=success_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
        logger.info(f"Notification sent to user {user.telegram_id}")
        
    except Exception as e:
        logger.error(f"Error sending notification to user {user.telegram_id}: {e}")


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