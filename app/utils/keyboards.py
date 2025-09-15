from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Основная клавиатура"""
    builder = ReplyKeyboardBuilder()
    
    builder.row(
        KeyboardButton(text="💬 Общение"),
        KeyboardButton(text="👤 Профиль девушки")
    )
    builder.row(
        KeyboardButton(text="💎 Подписка"),
        KeyboardButton(text="⚙️ Настройки")
    )
    builder.row(
        KeyboardButton(text="ℹ️ Помощь")
    )
    
    return builder.as_markup(resize_keyboard=True)


def get_subscription_keyboard(has_subscription: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для управления подпиской"""
    builder = InlineKeyboardBuilder()
    
    if not has_subscription:
        builder.row(
            InlineKeyboardButton(
                text="💳 Посмотреть тарифы",
                callback_data="view_plans"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🎁 Активировать пробный период",
                callback_data="activate_trial"
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text="💳 Продлить подписку",
                callback_data="view_plans"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="❌ Отменить подписку",
                callback_data="cancel_subscription"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text="📊 Информация о подписке",
            callback_data="subscription_info"
        )
    )
    
    return builder.as_markup()


def get_profile_keyboard(has_profile: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для управления профилем девушки"""
    builder = InlineKeyboardBuilder()
    
    if not has_profile:
        builder.row(
            InlineKeyboardButton(
                text="➕ Создать профиль",
                callback_data="create_profile"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🎲 Случайный профиль",
                callback_data="random_profile"
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text="👀 Посмотреть профиль",
                callback_data="view_profile"
            ),
            InlineKeyboardButton(
                text="✏️ Редактировать",
                callback_data="edit_profile"
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="🔄 Новый профиль",
                callback_data="create_profile"
            ),
            InlineKeyboardButton(
                text="🗑 Удалить профиль",
                callback_data="delete_profile"
            )
        )
    
    return builder.as_markup()


def get_profile_creation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для создания профиля"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="📝 Создать вручную",
            callback_data="create_manual"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🤖 Создать с помощью ИИ",
            callback_data="create_ai"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🎲 Случайный профиль",
            callback_data="create_random"
        )
    )
    
    return builder.as_markup()


def get_profile_edit_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для редактирования профиля"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="👤 Имя", callback_data="edit_name"),
        InlineKeyboardButton(text="🎂 Возраст", callback_data="edit_age")
    )
    builder.row(
        InlineKeyboardButton(text="💭 Характер", callback_data="edit_personality"),
        InlineKeyboardButton(text="👗 Внешность", callback_data="edit_appearance")
    )
    builder.row(
        InlineKeyboardButton(text="🎯 Интересы", callback_data="edit_interests"),
        InlineKeyboardButton(text="📖 История", callback_data="edit_background")
    )
    builder.row(
        InlineKeyboardButton(text="💬 Стиль общения", callback_data="edit_communication")
    )
    builder.row(
        InlineKeyboardButton(text="✅ Готово", callback_data="edit_done")
    )
    
    return builder.as_markup()


def get_conversation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для управления разговором"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="🗑 Очистить историю",
            callback_data="clear_history"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📊 Статистика",
            callback_data="conversation_stats"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад",
            callback_data="back_to_main"
        )
    )
    
    return builder.as_markup()


def get_payment_keyboard(payment_url: str) -> InlineKeyboardMarkup:
    """Клавиатура для оплаты"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="💳 Оплатить",
            url=payment_url
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="✅ Проверить оплату",
            callback_data="check_payment"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="❌ Отменить",
            callback_data="cancel_payment"
        )
    )
    
    return builder.as_markup()


def get_subscription_plans_keyboard(plans: list) -> InlineKeyboardMarkup:
    """Клавиатура с планами подписок"""
    builder = InlineKeyboardBuilder()
    
    for plan in plans:
        # Эмодзи для разных планов
        emoji_map = {
            "monthly": "📅",
            "quarterly": "📈", 
            "yearly": "🏆"
        }
        emoji = emoji_map.get(plan.plan_type, "💸")
        
        # Текст кнопки
        button_text = f"{emoji} {plan.name} - {plan.price}₽"
        if plan.is_popular:
            button_text = f"⭐ {button_text}"
        if plan.savings_percentage > 0:
            button_text += f" (-{plan.savings_percentage}%)"
            
        builder.row(
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"buy_plan_{plan.id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад",
            callback_data="back_to_subscription"
        )
    )
    
    return builder.as_markup()


def get_plan_details_keyboard(plan_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для подробностей плана"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="💳 Купить",
            callback_data=f"confirm_buy_plan_{plan_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 К списку планов",
            callback_data="view_plans"
        )
    )
    
    return builder.as_markup()


def get_confirmation_keyboard(action: str) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения действия"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="✅ Да",
            callback_data=f"confirm_{action}"
        ),
        InlineKeyboardButton(
            text="❌ Нет",
            callback_data=f"cancel_{action}"
        )
    )
    
    return builder.as_markup()