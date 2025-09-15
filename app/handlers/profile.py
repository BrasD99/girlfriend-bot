from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from app.services.database import db_service
from app.services.girlfriend_service import GirlfriendService
from app.services.gemini_service import GeminiService
from app.utils.keyboards import (
    get_profile_keyboard, get_profile_creation_keyboard, 
    get_profile_edit_keyboard, get_confirmation_keyboard
)
from app.utils.decorators import user_required, subscription_required, error_handler
from app.utils.helpers import format_profile_info, validate_age, validate_name, safe_edit_message
from app.utils.states import ProfileCreation, ProfileEditing
import logging

logger = logging.getLogger(__name__)
router = Router()

# Инициализируем сервис Gemini
gemini_service = GeminiService()


@router.message(Command("profile"))
@router.message(F.text == "👤 Профиль девушки")
@error_handler
@user_required
@subscription_required
async def profile_menu(message: types.Message, user):
    """Меню управления профилем девушки"""
    async with db_service.async_session() as session:
        profile = await GirlfriendService.get_active_profile(session, user.id)
        
        if profile:
            text = f"👤 **Активный профиль:**\n\n{format_profile_info(profile)}"
            keyboard = get_profile_keyboard(True)
        else:
            text = (
                "👤 **Профиль девушки**\n\n"
                "У вас пока нет созданного профиля девушки.\n"
                "Создайте профиль, чтобы начать общение!"
            )
            keyboard = get_profile_keyboard(False)
    
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")


@router.callback_query(F.data == "create_profile")
@error_handler
async def create_profile_callback(callback: types.CallbackQuery):
    """Выбор способа создания профиля"""
    text = (
        "👤 **Создание профиля девушки**\n\n"
        "Выберите способ создания:\n\n"
        "📝 **Вручную** - вы сами зададите все характеристики\n"
        "🤖 **С помощью ИИ** - опишите предпочтения, ИИ создаст профиль\n"
        "🎲 **Случайный** - ИИ создаст случайный профиль"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_profile_creation_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "create_manual")
@error_handler
async def create_manual_callback(callback: types.CallbackQuery, state: FSMContext):
    """Ручное создание профиля"""
    await state.set_state(ProfileCreation.waiting_for_name)
    
    text = (
        "👤 **Создание профиля вручную**\n\n"
        "Давайте создадим профиль вашей идеальной девушки!\n\n"
        "Шаг 1/6: Как зовут вашу девушку?\n"
        "Введите имя:"
    )
    
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "create_ai")
@error_handler
async def create_ai_callback(callback: types.CallbackQuery, state: FSMContext):
    """Создание профиля с помощью ИИ"""
    await state.set_state(ProfileCreation.waiting_for_preferences)
    
    text = (
        "🤖 **Создание профиля с помощью ИИ**\n\n"
        "Опишите, какую девушку вы хотели бы видеть:\n\n"
        "Например:\n"
        "• Добрая и веселая блондинка 25 лет\n"
        "• Умная брюнетка, любит книги и кино\n"
        "• Спортивная девушка с чувством юмора\n\n"
        "Опишите ваши предпочтения:"
    )
    
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "create_random")
@error_handler
@user_required
async def create_random_callback(callback: types.CallbackQuery, user):
    """Создание случайного профиля (из меню создания)"""
    await _create_random_profile(callback, user)


@router.callback_query(F.data == "random_profile")
@error_handler
@user_required
async def random_profile_callback(callback: types.CallbackQuery, user):
    """Создание случайного профиля (из главного меню профиля)"""
    await _create_random_profile(callback, user)


async def _create_random_profile(callback: types.CallbackQuery, user):
    """Общая логика создания случайного профиля"""
    await callback.message.edit_text("🎲 Создаю случайный профиль...")
    
    try:
        # Проверяем, нет ли уже активного профиля
        async with db_service.async_session() as session:
            existing_profile = await GirlfriendService.get_active_profile(session, user.id)
            
            if existing_profile:
                await callback.message.edit_text(
                    "⚠️ У вас уже есть активный профиль.\n\n"
                    "Удалите текущий профиль или создайте новый через меню 'Создать профиль'.",
                    reply_markup=get_profile_keyboard(True)
                )
                await callback.answer("⚠️ Профиль уже существует", show_alert=True)
                return
        
        # Генерируем случайный профиль
        profile_data = await gemini_service.generate_profile_suggestions(
            "Создай случайный профиль привлекательной девушки с уникальными чертами характера и внешности"
        )
        
        async with db_service.async_session() as session:
            profile = await GirlfriendService.create_girlfriend_profile(
                session,
                user,
                name=profile_data.get("name", "Анна"),
                age=profile_data.get("age", 23),
                personality=profile_data.get("personality", "Добрая и отзывчивая"),
                appearance=profile_data.get("appearance", "Привлекательная девушка"),
                interests=profile_data.get("interests", "Музыка, книги, путешествия"),
                background=profile_data.get("background", "Интересная и разносторонняя личность"),
                communication_style=profile_data.get("communication_style", "Общается дружелюбно и тепло")
            )
        
        success_text = (
            f"🎉 **Профиль создан!**\n\n"
            f"{format_profile_info(profile)}\n\n"
            f"🎲 **Случайный профиль готов!**\n"
            f"Теперь вы можете начать общение! 💕\n\n"
            f"⚙️ Если что-то не нравится, вы можете отредактировать профиль!"
        )
        
        await callback.message.edit_text(
            success_text,
            reply_markup=get_profile_keyboard(True),
            parse_mode="Markdown"
        )
        await callback.answer("✅ Случайный профиль создан!")
        
    except Exception as e:
        logger.error(f"Error creating random profile: {e}")
        await callback.message.edit_text(
            "❌ **Ошибка при создании профиля**\n\n"
            "Попробуйте еще раз или создайте профиль вручную.",
            reply_markup=get_profile_keyboard(False),
            parse_mode="Markdown"
        )
        await callback.answer("❌ Ошибка при создании профиля", show_alert=True)


# Обработчики для ручного создания профиля
@router.message(ProfileCreation.waiting_for_name)
@error_handler
@user_required
async def process_name(message: types.Message, state: FSMContext, user):
    """Обработка имени"""
    name = message.text.strip()
    
    if not validate_name(name):
        await message.answer(
            "❌ Пожалуйста, введите корректное имя (только буквы, минимум 2 символа)"
        )
        return
    
    await state.update_data(name=name)
    await state.set_state(ProfileCreation.waiting_for_age)
    
    await message.answer(
        f"✅ Имя: {name}\n\n"
        f"Шаг 2/6: Сколько лет вашей девушке?\n"
        f"Введите возраст (18-50):"
    )


@router.message(ProfileCreation.waiting_for_age)
@error_handler
async def process_age(message: types.Message, state: FSMContext):
    """Обработка возраста"""
    age = validate_age(message.text.strip())
    
    if not age:
        await message.answer(
            "❌ Пожалуйста, введите корректный возраст (от 18 до 50 лет)"
        )
        return
    
    await state.update_data(age=age)
    await state.set_state(ProfileCreation.waiting_for_personality)
    
    await message.answer(
        f"✅ Возраст: {age} лет\n\n"
        f"Шаг 3/6: Опишите характер вашей девушки\n"
        f"Например: добрая, веселая, умная, застенчивая..."
    )


@router.message(ProfileCreation.waiting_for_personality)
@error_handler
async def process_personality(message: types.Message, state: FSMContext):
    """Обработка характера"""
    personality = message.text.strip()
    
    if len(personality) < 10:
        await message.answer(
            "❌ Пожалуйста, опишите характер подробнее (минимум 10 символов)"
        )
        return
    
    await state.update_data(personality=personality)
    await state.set_state(ProfileCreation.waiting_for_appearance)
    
    await message.answer(
        f"✅ Характер сохранен\n\n"
        f"Шаг 4/6: Опишите внешность вашей девушки\n"
        f"Например: блондинка с голубыми глазами, высокая..."
    )


@router.message(ProfileCreation.waiting_for_appearance)
@error_handler
async def process_appearance(message: types.Message, state: FSMContext):
    """Обработка внешности"""
    appearance = message.text.strip()
    
    if len(appearance) < 10:
        await message.answer(
            "❌ Пожалуйста, опишите внешность подробнее (минимум 10 символов)"
        )
        return
    
    await state.update_data(appearance=appearance)
    await state.set_state(ProfileCreation.waiting_for_interests)
    
    await message.answer(
        f"✅ Внешность сохранена\n\n"
        f"Шаг 5/6: Какие у неё интересы и хобби?\n"
        f"Например: чтение, спорт, музыка, путешествия..."
    )


@router.message(ProfileCreation.waiting_for_interests)
@error_handler
async def process_interests(message: types.Message, state: FSMContext):
    """Обработка интересов"""
    interests = message.text.strip()
    
    await state.update_data(interests=interests)
    await state.set_state(ProfileCreation.waiting_for_background)
    
    await message.answer(
        f"✅ Интересы сохранены\n\n"
        f"Шаг 6/6: Расскажите о её предыстории\n"
        f"Например: студентка, работает дизайнером, живет в Москве..."
    )


@router.message(ProfileCreation.waiting_for_background)
@error_handler
@user_required
async def process_background(message: types.Message, state: FSMContext, user):
    """Обработка предыстории и создание профиля"""
    background = message.text.strip()
    
    data = await state.get_data()
    await state.clear()
    
    try:
        async with db_service.async_session() as session:
            profile = await GirlfriendService.create_girlfriend_profile(
                session,
                user,
                name=data["name"],
                age=data["age"],
                personality=data["personality"],
                appearance=data["appearance"],
                interests=data["interests"],
                background=background,
                communication_style="Общается дружелюбно и тепло"
            )
        
        success_text = (
            f"🎉 **Профиль создан!**\n\n"
            f"{format_profile_info(profile)}\n\n"
            f"Теперь вы можете начать общение! 💕"
        )
        
        await message.answer(
            success_text,
            reply_markup=get_profile_keyboard(True),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error creating profile: {e}")
        await message.answer("❌ Ошибка при создании профиля. Попробуйте еще раз.")


# Обработчик для создания профиля с помощью ИИ
@router.message(ProfileCreation.waiting_for_preferences)
@error_handler
@user_required
async def process_ai_preferences(message: types.Message, state: FSMContext, user):
    """Обработка предпочтений для ИИ"""
    preferences = message.text.strip()
    await state.clear()
    
    if len(preferences) < 10:
        await message.answer(
            "❌ Пожалуйста, опишите предпочтения подробнее (минимум 10 символов)"
        )
        return
    
    await message.answer("🤖 Создаю профиль на основе ваших предпочтений...")
    
    try:
        # Генерируем профиль с помощью ИИ
        profile_data = await gemini_service.generate_profile_suggestions(preferences)
        
        async with db_service.async_session() as session:
            profile = await GirlfriendService.create_girlfriend_profile(
                session,
                user,
                name=profile_data.get("name", "Анна"),
                age=profile_data.get("age", 23),
                personality=profile_data.get("personality", ""),
                appearance=profile_data.get("appearance", ""),
                interests=profile_data.get("interests", ""),
                background=profile_data.get("background", ""),
                communication_style=profile_data.get("communication_style", "")
            )
        
        success_text = (
            f"🎉 **Профиль создан с помощью ИИ!**\n\n"
            f"{format_profile_info(profile)}\n\n"
            f"Если что-то не нравится, вы можете отредактировать профиль! 💕"
        )
        
        await message.answer(
            success_text,
            reply_markup=get_profile_keyboard(True),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error creating AI profile: {e}")
        await message.answer("❌ Ошибка при создании профиля. Попробуйте еще раз.")


# Просмотр и редактирование профиля
@router.callback_query(F.data == "view_profile")
@error_handler
@user_required
async def view_profile_callback(callback: types.CallbackQuery, user):
    """Просмотр профиля"""
    async with db_service.async_session() as session:
        profile = await GirlfriendService.get_active_profile(session, user.id)
        
        if profile:
            text = f"👤 **Профиль девушки:**\n\n{format_profile_info(profile)}"
            await safe_edit_message(
                callback.message,
                text,
                reply_markup=get_profile_keyboard(True),
                parse_mode="Markdown"
            )
            await callback.answer("👤 Профиль обновлен")
        else:
            await callback.answer("❌ Профиль не найден", show_alert=True)


@router.callback_query(F.data == "edit_profile")
@error_handler
async def edit_profile_callback(callback: types.CallbackQuery):
    """Редактирование профиля"""
    text = (
        "✏️ **Редактирование профиля**\n\n"
        "Выберите, что хотите изменить:"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_profile_edit_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "delete_profile")
@error_handler
async def delete_profile_callback(callback: types.CallbackQuery):
    """Удаление профиля"""
    text = (
        "🗑 **Удаление профиля**\n\n"
        "⚠️ Вы уверены, что хотите удалить профиль?\n"
        "Это действие нельзя отменить!"
    )
    
    keyboard = get_confirmation_keyboard("profile_delete")
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "confirm_profile_delete")
@error_handler
@user_required
async def confirm_delete_profile(callback: types.CallbackQuery, user):
    """Подтверждение удаления профиля"""
    async with db_service.async_session() as session:
        profile = await GirlfriendService.get_active_profile(session, user.id)
        
        if profile:
            await GirlfriendService.delete_profile(session, profile.id, user.id)
            
            text = (
                "✅ Профиль удален\n\n"
                "Вы можете создать новый профиль в любое время."
            )
            
            await callback.message.edit_text(
                text,
                reply_markup=get_profile_keyboard(False)
            )
            await callback.answer("Профиль удален")
        else:
            await callback.answer("❌ Профиль не найден", show_alert=True)