from functools import wraps
from aiogram import types
from app.services.database import db_service
from app.services.user_service import UserService
from app.services.subscription_service import SubscriptionService
from app.services.redis_rate_limiter import redis_rate_limiter
import logging

logger = logging.getLogger(__name__)

def subscription_required(func):
    """Декоратор для проверки наличия активной подписки"""
    @wraps(func)
    async def wrapper(message_or_callback, *args, **kwargs):
        # Определяем тип объекта (сообщение или callback)
        if isinstance(message_or_callback, types.Message):
            user_id = message_or_callback.from_user.id
            chat_id = message_or_callback.chat.id
            bot = message_or_callback.bot
        elif isinstance(message_or_callback, types.CallbackQuery):
            user_id = message_or_callback.from_user.id
            chat_id = message_or_callback.message.chat.id
            bot = message_or_callback.bot
        else:
            logger.error("Unsupported object type in subscription_required decorator")
            return
        
        # Проверяем подписку
        async with db_service.async_session() as session:
            user = await UserService.get_user_by_telegram_id(session, user_id)
            if not user:
                await bot.send_message(
                    chat_id,
                    "❌ Пользователь не найден. Используйте /start для регистрации."
                )
                return
            
            has_subscription = await SubscriptionService.is_user_subscribed(session, user.id)
            if not has_subscription:
                await bot.send_message(
                    chat_id,
                    "❌ Для использования этой функции необходима активная подписка.\n\n"
                    "Используйте команду /subscription для оформления подписки."
                )
                return
        
        # Если подписка есть, выполняем функцию
        return await func(message_or_callback, *args, **kwargs)
    
    return wrapper


def rate_limit(func):
    """Декоратор для применения rate limiting"""
    @wraps(func)
    async def wrapper(message_or_callback, *args, **kwargs):
        # Определяем тип объекта и получаем user_id
        if isinstance(message_or_callback, types.Message):
            user_id = message_or_callback.from_user.id
            chat_id = message_or_callback.chat.id
            bot = message_or_callback.bot
            is_callback = False
        elif isinstance(message_or_callback, types.CallbackQuery):
            user_id = message_or_callback.from_user.id
            chat_id = message_or_callback.message.chat.id
            bot = message_or_callback.bot
            is_callback = True
        else:
            logger.error("Unsupported object type in rate_limit decorator")
            return
        
        # Проверяем rate limit
        limit_result = await redis_rate_limiter.check_rate_limit(user_id)
        
        # Если пользователь забанен
        if limit_result['banned']:
            ban_remaining = limit_result['ban_remaining']
            if ban_remaining > 0:
                ban_message = f"🚫 Слишком много действий! Попробуйте через {ban_remaining} сек."
                
                if is_callback:
                    # Для callback_query используем answer с show_alert
                    await message_or_callback.answer(ban_message, show_alert=True)
                else:
                    # Для обычных сообщений отправляем новое сообщение
                    await bot.send_message(
                        chat_id,
                        f"🚫 **Слишком много сообщений!**\n\n"
                        f"Вы временно ограничены в отправке сообщений.\n"
                        f"⏰ Попробуйте снова через {ban_remaining} сек.",
                        parse_mode="Markdown"
                    )
            # НЕ записываем сообщение, если пользователь забанен
            return
        
        # Если нужно показать предупреждение
        if limit_result['warning']:
            warning_message = f"⚠️ Внимание! Осталось действий: {limit_result['remaining']}"
            
            if is_callback:
                # Для callback_query используем answer без show_alert
                await message_or_callback.answer(warning_message, show_alert=False)
            else:
                # Для обычных сообщений отправляем новое сообщение
                await bot.send_message(
                    chat_id,
                    f"⚠️ **Внимание!**\n\n"
                    f"Вы отправляете сообщения слишком быстро.\n"
                    f"Осталось сообщений: {limit_result['remaining']}\n"
                    f"При превышении лимита вы будете временно ограничены.",
                    parse_mode="Markdown"
                )
        
        # Если лимит не превышен, записываем сообщение и выполняем функцию
        if limit_result['allowed']:
            # Записываем сообщение ТОЛЬКО если оно разрешено
            await redis_rate_limiter.record_message(user_id)
            return await func(message_or_callback, *args, **kwargs)
        else:
            # Лимит превышен, но пользователь еще не забанен (не должно происходить)
            limit_message = "🚫 Превышен лимит сообщений. Попробуйте позже."
            
            if is_callback:
                await message_or_callback.answer(limit_message, show_alert=True)
            else:
                await bot.send_message(chat_id, limit_message)
            # НЕ записываем сообщение, если лимит превышен
            return
    
    return wrapper


def user_required(func):
    """Декоратор для автоматической регистрации пользователя"""
    @wraps(func)
    async def wrapper(message_or_callback, *args, **kwargs):
        # Определяем тип объекта
        if isinstance(message_or_callback, types.Message):
            user_data = message_or_callback.from_user
        elif isinstance(message_or_callback, types.CallbackQuery):
            user_data = message_or_callback.from_user
        else:
            logger.error("Unsupported object type in user_required decorator")
            return
        
        # Регистрируем или получаем пользователя
        async with db_service.async_session() as session:
            user = await UserService.get_or_create_user(
                session,
                telegram_id=user_data.id,
                username=user_data.username,
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                language_code=user_data.language_code or "ru"
            )
        
        # Добавляем пользователя в kwargs
        kwargs['user'] = user
        
        return await func(message_or_callback, *args, **kwargs)
    
    return wrapper


def error_handler(func):
    """Декоратор для обработки ошибок"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            
            # Пытаемся отправить сообщение об ошибке пользователю
            message_or_callback = args[0] if args else None
            if isinstance(message_or_callback, (types.Message, types.CallbackQuery)):
                try:
                    if isinstance(message_or_callback, types.Message):
                        await message_or_callback.answer(
                            "❌ Произошла ошибка. Попробуйте позже или обратитесь в поддержку."
                        )
                    else:
                        await message_or_callback.answer(
                            "❌ Произошла ошибка. Попробуйте позже.",
                            show_alert=True
                        )
                except:
                    pass
    
    return wrapper