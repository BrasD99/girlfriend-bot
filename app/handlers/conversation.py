from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from app.models.girlfriend_profile import GirlfriendProfile
from app.services.database import db_service
from app.services.girlfriend_service import GirlfriendService
from app.services.conversation_service import ConversationService
from app.services.gemini_service import GeminiService
from app.utils.keyboards import get_conversation_keyboard, get_confirmation_keyboard
from app.utils.decorators import user_required, subscription_required, error_handler
from app.utils.helpers import format_conversation_stats
from app.utils.states import Conversation
import logging

logger = logging.getLogger(__name__)
router = Router()

# Инициализируем сервис Gemini
gemini_service = GeminiService()


@router.message(Command("chat"))
@router.message(F.text == "💬 Общение")
@error_handler
@user_required
@subscription_required
async def start_conversation(message: types.Message, state: FSMContext, user):
    """Начало общения с девушкой"""
    async with db_service.async_session() as session:
        profile = await GirlfriendService.get_active_profile(session, user.id)
        
        if not profile:
            await message.answer(
                "❌ У вас нет активного профиля девушки!\n\n"
                "Создайте профиль в разделе '👤 Профиль девушки', "
                "чтобы начать общение."
            )
            return
        
        # Устанавливаем состояние общения
        await state.set_state(Conversation.chatting)
        await state.update_data(profile_id=profile.id)
        
        # Получаем статистику разговора
        stats = await ConversationService.get_conversation_stats(
            session, user.id, profile.id
        )
        
        if stats["total_messages"] == 0:
            # Первое общение
            greeting_text = (
                f"💕 Привет! Меня зовут {profile.name}!\n\n"
                f"Я очень рада познакомиться с тобой! "
                f"Расскажи, как дела? Чем занимаешься? 😊"
            )
            
            # Сохраняем приветственное сообщение
            await ConversationService.save_message(
                session, user.id, profile.id, "assistant", greeting_text
            )
        else:
            # Продолжение общения
            greeting_text = (
                f"💕 Привет! Я {profile.name}, рада тебя снова видеть!\n\n"
                f"Как дела? Что нового? 😊"
            )
        
        info_text = (
            f"💬 **Общение с {profile.name}**\n\n"
            f"{greeting_text}\n\n"
            f"📊 Сообщений в истории: {stats['total_messages']}\n\n"
            f"Просто напишите сообщение для общения!"
        )
        
        await message.answer(
            info_text,
            reply_markup=get_conversation_keyboard(),
            parse_mode="Markdown"
        )


@router.message(Conversation.chatting)
@error_handler
@user_required
async def handle_conversation_message(message: types.Message, state: FSMContext, user):
    """Обработка сообщений в режиме общения"""
    # Проверяем, что это не команда или кнопка
    if message.text and (message.text.startswith('/') or message.text in [
        "💬 Общение", "👤 Профиль девушки", "💎 Подписка", "⚙️ Настройки", "ℹ️ Помощь"
    ]):
        return
    
    data = await state.get_data()
    profile_id = data.get("profile_id")
    
    if not profile_id:
        await message.answer("❌ Ошибка: профиль не найден. Начните общение заново.")
        await state.clear()
        return
    
    user_message = message.text
    if not user_message or len(user_message.strip()) == 0:
        await message.answer("❌ Пожалуйста, отправьте текстовое сообщение.")
        return
    
    # Показываем, что бот печатает
    await message.bot.send_chat_action(message.chat.id, "typing")
    
    async with db_service.async_session() as session:
        try:
            # Получаем профиль девушки
            profile = await session.get(GirlfriendProfile, profile_id)
            if not profile:
                await message.answer("❌ Профиль не найден.")
                await state.clear()
                return
            
            # Сохраняем сообщение пользователя
            await ConversationService.save_message(
                session, user.id, profile_id, "user", user_message
            )
            
            # Получаем контекст разговора
            context = await ConversationService.get_recent_context(
                session, user.id, profile_id, limit=10
            )
            
            # Модерируем контент
            if not await gemini_service.moderate_content(user_message):
                response = (
                    "Прости, но я не могу обсуждать такие темы... 😔\n"
                    "Давай поговорим о чем-то другом! 😊"
                )
            else:
                # Генерируем ответ от девушки
                response = await gemini_service.generate_response(
                    profile, user_message, context
                )
            
            # Сохраняем ответ девушки
            await ConversationService.save_message(
                session, user.id, profile_id, "assistant", response
            )
            
            # Отправляем ответ пользователю
            await message.answer(response)
            
        except Exception as e:
            logger.error(f"Error in conversation: {e}")
            await message.answer(
                "Прости, у меня сейчас проблемы... 😔\n"
                "Попробуй написать еще раз через минутку!"
            )


@router.callback_query(F.data == "clear_history")
@error_handler
async def clear_history_callback(callback: types.CallbackQuery):
    """Очистка истории разговора"""
    text = (
        "🗑 **Очистка истории**\n\n"
        "⚠️ Вы уверены, что хотите очистить всю историю разговора?\n"
        "Это действие нельзя отменить!"
    )
    
    keyboard = get_confirmation_keyboard("clear_history")
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "confirm_clear_history")
@error_handler
@user_required
async def confirm_clear_history(callback: types.CallbackQuery, state: FSMContext, user):
    """Подтверждение очистки истории"""
    data = await state.get_data()
    profile_id = data.get("profile_id")
    
    if not profile_id:
        await callback.answer("❌ Ошибка: профиль не найден", show_alert=True)
        return
    
    async with db_service.async_session() as session:
        count = await ConversationService.clear_conversation_history(
            session, user.id, profile_id
        )
        
        text = (
            f"✅ История очищена\n\n"
            f"Удалено сообщений: {count}\n"
            f"Теперь вы можете начать общение заново!"
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=get_conversation_keyboard()
        )
        await callback.answer("История очищена")


@router.callback_query(F.data == "cancel_clear_history")
@error_handler
async def cancel_clear_history(callback: types.CallbackQuery):
    """Отмена очистки истории"""
    await callback.message.edit_text(
        "Очистка истории отменена",
        reply_markup=get_conversation_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "conversation_stats")
@error_handler
@user_required
async def conversation_stats_callback(callback: types.CallbackQuery, state: FSMContext, user):
    """Статистика разговора"""
    data = await state.get_data()
    profile_id = data.get("profile_id")
    
    if not profile_id:
        await callback.answer("❌ Ошибка: профиль не найден", show_alert=True)
        return
    
    async with db_service.async_session() as session:
        stats = await ConversationService.get_conversation_stats(
            session, user.id, profile_id
        )
        
        text = format_conversation_stats(stats)
        
        await callback.message.edit_text(
            text,
            reply_markup=get_conversation_keyboard()
        )
        await callback.answer()


@router.callback_query(F.data == "back_to_main")
@error_handler
async def back_to_main_callback(callback: types.CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    
    from app.utils.keyboards import get_main_keyboard
    
    await callback.message.edit_text(
        "🏠 Главное меню\n\nВыберите действие:",
        reply_markup=None
    )
    
    # Отправляем новое сообщение с основной клавиатурой
    await callback.message.answer(
        "Используйте кнопки ниже для навигации:",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()


# Команда для выхода из режима общения
@router.message(Command("stop"))
@error_handler
async def stop_conversation(message: types.Message, state: FSMContext):
    """Выход из режима общения"""
    current_state = await state.get_state()
    
    if current_state == Conversation.chatting:
        await state.clear()
        
        from app.utils.keyboards import get_main_keyboard
        
        await message.answer(
            "✅ Общение завершено.\n\nВы можете вернуться к общению в любое время!",
            reply_markup=get_main_keyboard()
        )
    else:
        await message.answer("Вы не находитесь в режиме общения.")


# Обработчик для неизвестных сообщений вне режима общения
@router.message()
@error_handler
async def handle_unknown_message(message: types.Message, state: FSMContext):
    """Обработка неизвестных сообщений"""
    current_state = await state.get_state()
    
    # Если пользователь не в режиме общения, предлагаем помощь
    if current_state != Conversation.chatting:
        await message.answer(
            "🤔 Я не понимаю эту команду.\n\n"
            "Используйте кнопки меню или команду /help для получения справки."
        )