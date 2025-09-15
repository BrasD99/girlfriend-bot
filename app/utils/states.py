from aiogram.fsm.state import State, StatesGroup


class ProfileCreation(StatesGroup):
    """Состояния для создания профиля девушки"""
    waiting_for_user_description = State()  # Ожидание описания пользователя для ИИ
    waiting_for_preferences = State()  # Ожидание предпочтений для ИИ
    waiting_for_name = State()
    waiting_for_age = State()
    waiting_for_personality = State()
    waiting_for_appearance = State()
    waiting_for_interests = State()
    waiting_for_background = State()
    waiting_for_communication_style = State()


class ProfileEditing(StatesGroup):
    """Состояния для редактирования профиля"""
    waiting_for_name = State()
    waiting_for_age = State()
    waiting_for_personality = State()
    waiting_for_appearance = State()
    waiting_for_interests = State()
    waiting_for_background = State()
    waiting_for_communication_style = State()


class Conversation(StatesGroup):
    """Состояния для общения"""
    chatting = State()  # Активное общение с девушкой


class Payment(StatesGroup):
    """Состояния для оплаты"""
    waiting_for_payment = State()  # Ожидание оплаты