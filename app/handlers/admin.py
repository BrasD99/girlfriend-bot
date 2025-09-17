from aiogram import Router, types
from aiogram.filters import Command
from app.utils.decorators import error_handler
from config.settings import settings
import logging

logger = logging.getLogger(__name__)
router = Router()


def is_admin(user_id: int, username: str = None) -> bool:
    """Проверка, является ли пользователь администратором"""
    if settings.admin_username and username:
        return username.lower() == settings.admin_username.lower()
    return False


@router.message(Command("admin_notifications"))
@error_handler
async def admin_notifications_command(message: types.Message):
    """Административная команда для управления уведомлениями"""
    if not is_admin(message.from_user.id, message.from_user.username):
        await message.answer("❌ У вас нет прав для выполнения этой команды")
        return
    
    from main import scheduler_service
    
    if not scheduler_service:
        await message.answer("❌ Планировщик уведомлений не инициализирован")
        return
    
    # Получаем информацию о задачах
    jobs_info = scheduler_service.get_jobs_info()
    
    status_text = (
        f"📊 **Статус системы уведомлений**\\n\\n"
        f"🔧 Уведомления включены: {'✅ Да' if settings.enable_subscription_notifications else '❌ Нет'}\\n"
        f"⏰ Интервал проверки: {settings.notification_check_interval_hours} часов\\n"
        f"📅 Уведомлять за: {settings.subscription_expiry_notification_days} дней\\n\\n"
        f"**Запланированные задачи:**\\n"
    )
    
    if jobs_info:
        for job in jobs_info:
            status_text += f"• {job['name']} (ID: {job['id']})\\n"
            if job['next_run']:
                status_text += f"  Следующий запуск: {job['next_run']}\\n"
    else:
        status_text += "Нет активных задач\\n"
    
    status_text += "\\n💡 Используйте /admin_check_notifications для принудительной проверки"
    
    await message.answer(status_text, parse_mode="Markdown")


@router.message(Command("admin_check_notifications"))
@error_handler
async def admin_check_notifications_command(message: types.Message):
    """Принудительная проверка уведомлений"""
    if not is_admin(message.from_user.id, message.from_user.username):
        await message.answer("❌ У вас нет прав для выполнения этой команды")
        return
    
    from main import scheduler_service
    
    if not scheduler_service:
        await message.answer("❌ Планировщик уведомлений не инициализирован")
        return
    
    await message.answer("🔄 Запускаю проверку уведомлений...")
    
    try:
        stats = await scheduler_service.run_notification_check_now()
        
        result_text = (
            f"✅ **Проверка завершена**\\n\\n"
            f"📤 Предупреждений об истечении: {stats['expiry_warnings']}\\n"
            f"❌ Уведомлений об истечении: {stats['expired_notifications']}\\n"
            f"⚠️ Ошибок: {stats['errors']}"
        )
        
        await message.answer(result_text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error in manual notification check: {e}")
        await message.answer(f"❌ Ошибка при проверке уведомлений: {str(e)}")


@router.message(Command("admin_help"))
@error_handler
async def admin_help_command(message: types.Message):
    """Справка по административным командам"""
    if not is_admin(message.from_user.id, message.from_user.username):
        await message.answer("❌ У вас нет прав для выполнения этой команды")
        return
    
    help_text = (
        "🔧 **Административные команды**\\n\\n"
        "📊 `/admin_notifications` - статус системы уведомлений\\n"
        "🔄 `/admin_check_notifications` - принудительная проверка\\n"
        "❓ `/admin_help` - эта справка\\n\\n"
        "**Настройки уведомлений (.env):**\\n"
        "• `SUBSCRIPTION_EXPIRY_NOTIFICATION_DAYS` - за сколько дней уведомлять\\n"
        "• `NOTIFICATION_CHECK_INTERVAL_HOURS` - интервал проверки\\n"
        "• `ENABLE_SUBSCRIPTION_NOTIFICATIONS` - включить/выключить"
    )
    
    await message.answer(help_text, parse_mode="Markdown")