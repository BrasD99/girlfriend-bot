from datetime import datetime, timedelta, timezone
from app.models import Subscription, GirlfriendProfile
from typing import Optional


def utc_to_moscow_time(utc_datetime: datetime) -> datetime:
    """Конвертация UTC времени в московское время (UTC+3)"""
    if utc_datetime.tzinfo is None:
        # Если timezone не указан, считаем что это UTC
        utc_datetime = utc_datetime.replace(tzinfo=timezone.utc)
    
    # Московское время UTC+3
    moscow_tz = timezone(timedelta(hours=3))
    return utc_datetime.astimezone(moscow_tz)


def format_datetime_for_user(dt: datetime, include_time: bool = True) -> str:
    """Форматирование даты и времени для отображения пользователю в московском времени"""
    if not isinstance(dt, datetime):
        return str(dt)
    
    moscow_dt = utc_to_moscow_time(dt)
    
    if include_time:
        return moscow_dt.strftime("%d.%m.%Y %H:%M (МСК)")
    else:
        return moscow_dt.strftime("%d.%m.%Y")


def format_subscription_info(subscription_info: dict) -> str:
    """Форматирование информации о подписке"""
    # Если нет подписки вообще или она истекла
    if not subscription_info["has_subscription"]:
        # Проверяем, была ли подписка отменена
        if subscription_info.get("is_cancelled"):
            end_date = subscription_info["end_date"]
            if isinstance(end_date, datetime):
                end_date_str = format_datetime_for_user(end_date, include_time=False)
            else:
                end_date_str = str(end_date)
            
            return (
                "❌ Подписка отменена\n\n"
                "🔄 Автопродление отключено\n"
                f"📅 Доступ сохранится до {end_date_str}\n\n"
                "Вы можете возобновить подписку в любое время."
            )
        else:
            return (
                "❌ У вас нет активной подписки\n\n"
                "💎 Оформите подписку для доступа ко всем функциям бота:\n"
                "• Неограниченное общение с девушкой\n"
                "• Создание и редактирование профилей\n"
                "• Сохранение истории разговоров\n"
                "• Приоритетная поддержка\n\n"
                "💰 Стоимость: 299₽/месяц"
            )
    
    status_emoji = "🎁" if subscription_info["is_trial"] else "💎"
    status_text = "Пробный период" if subscription_info["is_trial"] else "Активная подписка"
    
    end_date = subscription_info["end_date"]
    if isinstance(end_date, datetime):
        end_date_str = format_datetime_for_user(end_date, include_time=True)
    else:
        end_date_str = str(end_date)
    
    days_left = subscription_info["days_left"]
    
    return (
        f"{status_emoji} {status_text}\n\n"
        f"📅 Действует до: {end_date_str}\n"
        f"⏰ Осталось дней: {days_left}\n\n"
        f"{'🔄 Не забудьте продлить подписку!' if days_left <= 3 else '✅ Все функции доступны'}"
    )


def format_profile_info(profile: GirlfriendProfile) -> str:
    """Форматирование информации о профиле девушки"""
    info_parts = [f"👤 **{profile.name}**"]
    
    if profile.age:
        info_parts.append(f"🎂 Возраст: {profile.age} лет")
    
    if profile.personality:
        info_parts.append(f"💭 Характер: {profile.personality}")
    
    if profile.appearance:
        info_parts.append(f"👗 Внешность: {profile.appearance}")
    
    if profile.interests:
        info_parts.append(f"🎯 Интересы: {profile.interests}")
    
    if profile.background:
        info_parts.append(f"📖 История: {profile.background}")
    
    if profile.communication_style:
        info_parts.append(f"💬 Стиль общения: {profile.communication_style}")
    
    return "\n\n".join(info_parts)


def format_conversation_stats(stats: dict) -> str:
    """Форматирование статистики разговора"""
    if stats["total_messages"] == 0:
        return "📊 Статистика разговора:\n\nВы еще не начали общение с девушкой."
    
    first_date = stats["first_message_date"]
    last_date = stats["last_message_date"]
    
    if isinstance(first_date, datetime):
        first_date_str = format_datetime_for_user(first_date, include_time=False)
    else:
        first_date_str = "Неизвестно"
    
    if isinstance(last_date, datetime):
        last_date_str = format_datetime_for_user(last_date, include_time=True)
    else:
        last_date_str = "Неизвестно"
    
    return (
        f"📊 Статистика разговора:\n\n"
        f"💬 Всего сообщений: {stats['total_messages']}\n"
        f"👤 Ваших сообщений: {stats['user_messages']}\n"
        f"💕 Сообщений девушки: {stats['assistant_messages']}\n\n"
        f"📅 Первое сообщение: {first_date_str}\n"
        f"🕐 Последнее сообщение: {last_date_str}"
    )


def validate_age(age_str: str) -> Optional[int]:
    """Валидация возраста"""
    try:
        age = int(age_str)
        if 18 <= age <= 50:
            return age
        return None
    except ValueError:
        return None


def validate_name(name: str) -> bool:
    """Валидация имени"""
    if not name or len(name.strip()) < 2:
        return False
    
    # Проверяем, что имя содержит только буквы и пробелы
    return all(c.isalpha() or c.isspace() for c in name.strip())


def truncate_text(text: str, max_length: int = 100) -> str:
    """Обрезание текста до указанной длины"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."


def get_greeting_message() -> str:
    """Получение приветственного сообщения в зависимости от времени (по московскому времени)"""
    # Получаем текущее время в Москве
    moscow_time = utc_to_moscow_time(datetime.now(timezone.utc))
    current_hour = moscow_time.hour
    
    if 5 <= current_hour < 12:
        return "Доброе утро! ☀️"
    elif 12 <= current_hour < 17:
        return "Добрый день! 🌤️"
    elif 17 <= current_hour < 22:
        return "Добрый вечер! 🌆"
    else:
        return "Доброй ночи! 🌙"


def format_payment_amount(amount: float) -> str:
    """Форматирование суммы платежа"""
    return f"{amount:.0f}₽"


def is_trial_expired(trial_start_date: datetime, trial_days: int) -> bool:
    """Проверка истечения пробного периода"""
    if not trial_start_date:
        return True
    
    expiry_date = trial_start_date + timedelta(days=trial_days)
    current_time = datetime.now(timezone.utc)
    
    # Если trial_start_date не содержит timezone, считаем его UTC
    if trial_start_date.tzinfo is None:
        trial_start_date = trial_start_date.replace(tzinfo=timezone.utc)
        expiry_date = trial_start_date + timedelta(days=trial_days)
    
    return current_time > expiry_date


async def safe_edit_message(message, new_text: str, reply_markup=None, parse_mode=None):
    """Безопасное редактирование сообщения (избегает ошибки 'message is not modified')"""
    current_text = message.text or ""
    current_markup = message.reply_markup
    
    # Проверяем, отличается ли новый контент
    text_changed = current_text != new_text
    markup_changed = current_markup != reply_markup
    
    if text_changed or markup_changed:
        kwargs = {"text": new_text}
        if reply_markup is not None:
            kwargs["reply_markup"] = reply_markup
        if parse_mode is not None:
            kwargs["parse_mode"] = parse_mode
            
        await message.edit_text(**kwargs)
        return True
    return False