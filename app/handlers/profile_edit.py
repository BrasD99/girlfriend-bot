from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from app.services.database import db_service
from app.services.girlfriend_service import GirlfriendService
from app.utils.keyboards import get_profile_edit_keyboard, get_profile_keyboard, get_cancel_keyboard
from app.utils.decorators import user_required, error_handler
from app.utils.helpers import format_profile_info, validate_age, validate_name
from app.utils.states import ProfileEditing
import logging

logger = logging.getLogger(__name__)
router = Router()

# Обработчики для редактирования профиля
@router.callback_query(F.data == "edit_name")
@error_handler
async def edit_name_callback(callback: types.CallbackQuery, state: FSMContext):
    """Редактирование имени"""
    await state.set_state(ProfileEditing.waiting_for_name)
    
    text = (
        "✏️ **Редактирование имени**\n\n"
        "Введите новое имя для вашей девушки:"
    )
    
    await callback.message.edit_text(text, reply_markup=get_cancel_keyboard(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "edit_age")
@error_handler
async def edit_age_callback(callback: types.CallbackQuery, state: FSMContext):
    """Редактирование возраста"""
    await state.set_state(ProfileEditing.waiting_for_age)
    
    text = (
        "✏️ **Редактирование возраста**\n\n"
        "Введите новый возраст (18-50):"
    )
    
    await callback.message.edit_text(text, reply_markup=get_cancel_keyboard(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "edit_personality")
@error_handler
async def edit_personality_callback(callback: types.CallbackQuery, state: FSMContext):
    """Редактирование характера"""
    await state.set_state(ProfileEditing.waiting_for_personality)
    
    text = (
        "✏️ **Редактирование характера**\n\n"
        "Опишите характер вашей девушки:\n"
        "Например: добрая, веселая, умная, застенчивая..."
    )
    
    await callback.message.edit_text(text, reply_markup=get_cancel_keyboard(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "edit_appearance")
@error_handler
async def edit_appearance_callback(callback: types.CallbackQuery, state: FSMContext):
    """Редактирование внешности"""
    await state.set_state(ProfileEditing.waiting_for_appearance)
    
    text = (
        "✏️ **Редактирование внешности**\n\n"
        "Опишите внешность вашей девушки:\n"
        "Например: блондинка с голубыми глазами, высокая..."
    )
    
    await callback.message.edit_text(text, reply_markup=get_cancel_keyboard(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "edit_interests")
@error_handler
async def edit_interests_callback(callback: types.CallbackQuery, state: FSMContext):
    """Редактирование интересов"""
    await state.set_state(ProfileEditing.waiting_for_interests)
    
    text = (
        "✏️ **Редактирование интересов**\n\n"
        "Какие у неё интересы и хобби?\n"
        "Например: чтение, спорт, музыка, путешествия..."
    )
    
    await callback.message.edit_text(text, reply_markup=get_cancel_keyboard(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "edit_background")
@error_handler
async def edit_background_callback(callback: types.CallbackQuery, state: FSMContext):
    """Редактирование предыстории"""
    await state.set_state(ProfileEditing.waiting_for_background)
    
    text = (
        "✏️ **Редактирование предыстории**\n\n"
        "Расскажите о её предыстории:\n"
        "Например: студентка, работает дизайнером, живет в Москве..."
    )
    
    await callback.message.edit_text(text, reply_markup=get_cancel_keyboard(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "edit_communication")
@error_handler
async def edit_communication_callback(callback: types.CallbackQuery, state: FSMContext):
    """Редактирование стиля общения"""
    await state.set_state(ProfileEditing.waiting_for_communication_style)
    
    text = (
        "✏️ **Редактирование стиля общения**\n\n"
        "Опишите, как она общается:\n"
        "Например: дружелюбно и тепло, игриво, серьезно..."
    )
    
    await callback.message.edit_text(text, reply_markup=get_cancel_keyboard(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "edit_done")
@error_handler
@user_required
async def edit_done_callback(callback: types.CallbackQuery, user):
    """Завершение редактирования"""
    async with db_service.async_session() as session:
        profile = await GirlfriendService.get_active_profile(session, user.id)
        
        if profile:
            text = (
                "✅ **Редактирование завершено**\n\n"
                f"{format_profile_info(profile)}"
            )
            
            await callback.message.edit_text(
                text,
                reply_markup=get_profile_keyboard(True),
                parse_mode="Markdown"
            )
            await callback.answer("✅ Изменения сохранены")
        else:
            await callback.answer("❌ Профиль не найден", show_alert=True)


# Обработчики сообщений для редактирования профиля
@router.message(ProfileEditing.waiting_for_name)
@error_handler
@user_required
async def process_edit_name(message: types.Message, state: FSMContext, user):
    """Обработка нового имени"""
    name = message.text.strip()
    
    if not validate_name(name):
        await message.answer(
            "❌ Пожалуйста, введите корректное имя (только буквы, минимум 2 символа)"
        )
        return
    
    async with db_service.async_session() as session:
        profile = await GirlfriendService.get_active_profile(session, user.id)
        
        if profile:
            await GirlfriendService.update_profile_field(session, profile.id, "name", name)
            await state.clear()
            
            text = (
                f"✅ **Имя изменено на: {name}**\n\n"
                "Что еще хотите изменить?"
            )
            
            await message.answer(
                text,
                reply_markup=get_profile_edit_keyboard(),
                parse_mode="Markdown"
            )
        else:
            await message.answer("❌ Профиль не найден")
            await state.clear()


@router.message(ProfileEditing.waiting_for_age)
@error_handler
@user_required
async def process_edit_age(message: types.Message, state: FSMContext, user):
    """Обработка нового возраста"""
    age = validate_age(message.text.strip())
    
    if not age:
        await message.answer(
            "❌ Пожалуйста, введите корректный возраст (от 18 до 50 лет)"
        )
        return
    
    async with db_service.async_session() as session:
        profile = await GirlfriendService.get_active_profile(session, user.id)
        
        if profile:
            await GirlfriendService.update_profile_field(session, profile.id, "age", age)
            await state.clear()
            
            text = (
                f"✅ **Возраст изменен на: {age} лет**\n\n"
                "Что еще хотите изменить?"
            )
            
            await message.answer(
                text,
                reply_markup=get_profile_edit_keyboard(),
                parse_mode="Markdown"
            )
        else:
            await message.answer("❌ Профиль не найден")
            await state.clear()


@router.message(ProfileEditing.waiting_for_personality)
@error_handler
@user_required
async def process_edit_personality(message: types.Message, state: FSMContext, user):
    """Обработка нового характера"""
    personality = message.text.strip()
    
    if len(personality) < 10:
        await message.answer(
            "❌ Пожалуйста, опишите характер подробнее (минимум 10 символов)"
        )
        return
    
    async with db_service.async_session() as session:
        profile = await GirlfriendService.get_active_profile(session, user.id)
        
        if profile:
            await GirlfriendService.update_profile_field(session, profile.id, "personality", personality)
            await state.clear()
            
            text = (
                "✅ **Характер изменен**\n\n"
                "Что еще хотите изменить?"
            )
            
            await message.answer(
                text,
                reply_markup=get_profile_edit_keyboard(),
                parse_mode="Markdown"
            )
        else:
            await message.answer("❌ Профиль не найден")
            await state.clear()


@router.message(ProfileEditing.waiting_for_appearance)
@error_handler
@user_required
async def process_edit_appearance(message: types.Message, state: FSMContext, user):
    """Обработка новой внешности"""
    appearance = message.text.strip()
    
    if len(appearance) < 10:
        await message.answer(
            "❌ Пожалуйста, опишите внешность подробнее (минимум 10 символов)"
        )
        return
    
    async with db_service.async_session() as session:
        profile = await GirlfriendService.get_active_profile(session, user.id)
        
        if profile:
            await GirlfriendService.update_profile_field(session, profile.id, "appearance", appearance)
            await state.clear()
            
            text = (
                "✅ **Внешность изменена**\n\n"
                "Что еще хотите изменить?"
            )
            
            await message.answer(
                text,
                reply_markup=get_profile_edit_keyboard(),
                parse_mode="Markdown"
            )
        else:
            await message.answer("❌ Профиль не найден")
            await state.clear()


@router.message(ProfileEditing.waiting_for_interests)
@error_handler
@user_required
async def process_edit_interests(message: types.Message, state: FSMContext, user):
    """Обработка новых интересов"""
    interests = message.text.strip()
    
    async with db_service.async_session() as session:
        profile = await GirlfriendService.get_active_profile(session, user.id)
        
        if profile:
            await GirlfriendService.update_profile_field(session, profile.id, "interests", interests)
            await state.clear()
            
            text = (
                "✅ **Интересы изменены**\n\n"
                "Что еще хотите изменить?"
            )
            
            await message.answer(
                text,
                reply_markup=get_profile_edit_keyboard(),
                parse_mode="Markdown"
            )
        else:
            await message.answer("❌ Профиль не найден")
            await state.clear()


@router.message(ProfileEditing.waiting_for_background)
@error_handler
@user_required
async def process_edit_background(message: types.Message, state: FSMContext, user):
    """Обработка новой предыстории"""
    background = message.text.strip()
    
    async with db_service.async_session() as session:
        profile = await GirlfriendService.get_active_profile(session, user.id)
        
        if profile:
            await GirlfriendService.update_profile_field(session, profile.id, "background", background)
            await state.clear()
            
            text = (
                "✅ **Предыстория изменена**\n\n"
                "Что еще хотите изменить?"
            )
            
            await message.answer(
                text,
                reply_markup=get_profile_edit_keyboard(),
                parse_mode="Markdown"
            )
        else:
            await message.answer("❌ Профиль не найден")
            await state.clear()


@router.message(ProfileEditing.waiting_for_communication_style)
@error_handler
@user_required
async def process_edit_communication_style(message: types.Message, state: FSMContext, user):
    """Обработка нового стиля общения"""
    communication_style = message.text.strip()
    
    async with db_service.async_session() as session:
        profile = await GirlfriendService.get_active_profile(session, user.id)
        
        if profile:
            await GirlfriendService.update_profile_field(session, profile.id, "communication_style", communication_style)
            await state.clear()
            
            text = (
                "✅ **Стиль общения изменен**\n\n"
                "Что еще хотите изменить?"
            )
            
            await message.answer(
                text,
                reply_markup=get_profile_edit_keyboard(),
                parse_mode="Markdown"
            )
        else:
            await message.answer("❌ Профиль не найден")
            await state.clear()


# Обработчик отмены редактирования
@router.callback_query(F.data == "cancel_edit")
@error_handler
@user_required
async def cancel_edit_callback(callback: types.CallbackQuery, state: FSMContext, user):
    """Отмена редактирования"""
    await state.clear()
    
    async with db_service.async_session() as session:
        profile = await GirlfriendService.get_active_profile(session, user.id)
        
        if profile:
            text = (
                "❌ **Редактирование отменено**\n\n"
                f"{format_profile_info(profile)}"
            )
            
            await callback.message.edit_text(
                text,
                reply_markup=get_profile_keyboard(True),
                parse_mode="Markdown"
            )
            await callback.answer("Редактирование отменено")
        else:
            await callback.answer("❌ Профиль не найден", show_alert=True)