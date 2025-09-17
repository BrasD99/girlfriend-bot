from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from app.services.database import db_service
from app.services.user_service import UserService
from app.services.subscription_service import SubscriptionService

from app.utils.keyboards import get_main_keyboard
from app.utils.decorators import user_required, error_handler
from app.utils.helpers import get_greeting_message
from config.settings import settings
import logging

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("start"))
@error_handler
@user_required
async def start_command(message: types.Message, state: FSMContext, user):
    """Обработчик команды /start"""
    await state.clear()
    
    greeting = get_greeting_message()
    
    async with db_service.async_session() as session:
        subscription_info = await SubscriptionService.get_subscription_info(session, user.id)
        
        # Проверяем, новый ли это пользователь (не использовал пробный период и нет подписки)
        if not user.trial_used and not subscription_info["has_subscription"]:
            try:
                # Автоматически активируем пробный период
                await UserService.start_trial(session, user)
                await SubscriptionService.create_trial_subscription(session, user)
                
                logger.info(f"Auto-activated trial for new user: {user.telegram_id}")
                
                # Приветствие для нового пользователя с уведомлением об активации пробного периода
                welcome_text = (
                    f"{greeting}\n\n"
                    f"🎉 **Добро пожаловать в бота-компаньона!** 💕\n\n"
                    f"✅ **Пробный период активирован!**\n"
                    f"🎁 Вам предоставлено **{settings.trial_days} дней** бесплатного доступа ко всем функциям!\n\n"
                    f"**Что вы можете делать:**\n"
                    f"• 💬 Общаться с виртуальной девушкой\n"
                    f"• 👤 Настроить ее характер и внешность\n"
                    f"• 💭 Вести приватные разговоры\n"
                    f"• 📱 Пользоваться всеми функциями без ограничений\n\n"
                    f"**Начните с создания профиля девушки!** 👤\n\n"
                    f"Используйте кнопки ниже для навигации:"
                )
                
            except Exception as e:
                logger.error(f"Failed to activate trial for user {user.telegram_id}: {e}")
                # Если не удалось активировать пробный период, показываем обычное приветствие
                welcome_text = (
                    f"{greeting}\n\n"
                    f"Добро пожаловать в бота-компаньона! 💕\n\n"
                    f"Здесь вы можете:\n"
                    f"• 💬 Общаться с виртуальной девушкой\n"
                    f"• 👤 Настроить ее характер и внешность\n"
                    f"• 💭 Вести приватные разговоры\n\n"
                    f"🎁 Для новых пользователей доступен бесплатный пробный период на {settings.trial_days} дней!\n\n"
                    f"Перейдите в раздел '💎 Подписка' для активации.\n\n"
                    f"Используйте кнопки ниже для навигации:"
                )
        else:
            # Существующий пользователь или уже есть подписка
            if subscription_info["has_subscription"]:
                status_text = "🎁 Пробный период" if subscription_info["is_trial"] else "💎 Активная подписка"
                days_left = subscription_info["days_left"]
                
                welcome_text = (
                    f"{greeting}\n\n"
                    f"С возвращением! 💕\n\n"
                    f"📊 **Статус:** {status_text}\n"
                    f"⏰ **Осталось дней:** {days_left}\n\n"
                    f"✅ Все функции доступны!\n\n"
                    f"Используйте кнопки ниже для навигации:"
                )
            else:
                # Пользователь уже использовал пробный период, но подписки нет
                welcome_text = (
                    f"{greeting}\n\n"
                    f"С возвращением! 💕\n\n"
                    f"💡 Пробный период уже использован.\n"
                    f"💎 Оформите подписку для доступа ко всем функциям!\n\n"
                    f"Используйте кнопки ниже для навигации:"
                )
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )


@router.message(Command("help"))
@error_handler
async def help_command(message: types.Message):
    """Обработчик команды /help"""
    # Формируем ссылку на поддержку
    support_text = "По всем вопросам обращайтесь в поддержку"
    if settings.admin_username:
        support_text = f"По всем вопросам обращайтесь: @{settings.admin_username}"
    
    help_text = (
        "🤖 **Помощь по использованию бота**\n\n"
        
        "**Основные команды:**\n"
        "/start - Главное меню\n"
        "/help - Эта справка\n"
        "/subscription - Управление подпиской\n"
        "/profile - Управление профилем девушки\n"
        "/chat - Начать общение\n\n"
        
        "**Как пользоваться:**\n"
        "1️⃣ Создайте профиль девушки в разделе '👤 Профиль девушки'\n"
        "2️⃣ Настройте ее характер, внешность и интересы\n"
        "3️⃣ Начните общение в разделе '💬 Общение'\n\n"
        
        "**Подписка:**\n"
        "• 💰 Посмотреть все тарифы: /subscription\n\n"
        
        f"**Поддержка:**\n"
        f"{support_text}"
    )
    
    await message.answer(help_text, parse_mode="Markdown")


@router.message(F.text == "ℹ️ Помощь")
@error_handler
async def help_button(message: types.Message):
    """Обработчик кнопки помощи"""
    await help_command(message)