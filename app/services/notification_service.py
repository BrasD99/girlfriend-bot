from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models import User, Subscription, SubscriptionStatus
from app.services.subscription_service import SubscriptionService, get_current_utc_time
from app.services.database import db_service
from app.utils.helpers import format_datetime_for_user
from app.utils.keyboards import get_subscription_keyboard
from datetime import timedelta
from config.settings import settings
from typing import List
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    @staticmethod
    async def get_users_with_expiring_subscriptions(
        session: AsyncSession, 
        days_before: int = None
    ) -> List[tuple[User, Subscription]]:
        """Получение пользователей с истекающими подписками"""
        if days_before is None:
            days_before = settings.subscription_expiry_notification_days
        
        current_time = get_current_utc_time()
        notification_threshold = current_time + timedelta(days=days_before)
        
        # Ищем активные подписки, которые истекают в ближайшие N дней
        result = await session.execute(
            select(User, Subscription)
            .join(Subscription, User.id == Subscription.user_id)
            .where(
                and_(
                    Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]),
                    Subscription.end_date <= notification_threshold,
                    Subscription.end_date > current_time,
                    # Проверяем, что уведомление еще не отправлялось или отправлялось давно
                    User.last_expiry_notification_sent.is_(None) |
                    (User.last_expiry_notification_sent < current_time - timedelta(hours=12))
                )
            )
        )
        
        return result.all()
    
    @staticmethod
    async def get_users_with_expired_subscriptions(session: AsyncSession) -> List[tuple[User, Subscription]]:
        """Получение пользователей с истекшими подписками"""
        current_time = get_current_utc_time()
        
        # Ищем подписки, которые истекли в последние 24 часа
        expired_threshold = current_time - timedelta(hours=24)
        
        result = await session.execute(
            select(User, Subscription)
            .join(Subscription, User.id == Subscription.user_id)
            .where(
                and_(
                    Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]),
                    Subscription.end_date <= current_time,
                    Subscription.end_date >= expired_threshold,
                    # Проверяем, что уведомление об истечении еще не отправлялось
                    User.last_expired_notification_sent.is_(None) |
                    (User.last_expired_notification_sent < Subscription.end_date)
                )
            )
        )
        
        return result.all()
    
    @staticmethod
    async def send_expiry_warning_notification(
        user: User, 
        subscription: Subscription,
        bot,
        session: AsyncSession
    ) -> bool:
        """Отправка предупреждения об истечении подписки"""
        try:
            days_left = (subscription.end_date - get_current_utc_time()).days
            hours_left = (subscription.end_date - get_current_utc_time()).total_seconds() / 3600
            
            if days_left <= 0 and hours_left > 0:
                time_text = f"менее чем через {int(hours_left)} часов"
            elif days_left == 1:
                time_text = "завтра"
            else:
                time_text = f"через {days_left} дней"
            
            status_text = "пробный период" if subscription.status == SubscriptionStatus.TRIAL else "подписка"
            
            warning_text = (
                f"⚠️ **Внимание!**\\n\\n"
                f"Ваш {status_text} истекает {time_text}\\n"
                f"📅 Дата окончания: {format_datetime_for_user(subscription.end_date)}\\n\\n"
                f"💡 Чтобы продолжить пользоваться всеми функциями бота:\\n"
                f"• Оформите новую подписку\\n"
                f"• Выберите подходящий план\\n"
                f"• Получите скидку при покупке длительных планов\\n\\n"
                f"💎 Не упустите возможность продолжить общение с вашей виртуальной девушкой!"
            )
            
            # Получаем информацию о подписке для клавиатуры
            subscription_info = await SubscriptionService.get_subscription_info(session, user.id)
            keyboard = get_subscription_keyboard(subscription_info)
            
            await bot.send_message(
                chat_id=user.telegram_id,
                text=warning_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            
            # Обновляем время отправки уведомления
            user.last_expiry_notification_sent = get_current_utc_time()
            await session.commit()
            
            logger.info(f"Expiry warning sent to user {user.telegram_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending expiry warning to user {user.telegram_id}: {e}")
            return False
    
    @staticmethod
    async def send_expired_notification(
        user: User, 
        subscription: Subscription,
        bot,
        session: AsyncSession
    ) -> bool:
        """Отправка уведомления об истечении подписки"""
        try:
            status_text = "пробный период" if subscription.status == SubscriptionStatus.TRIAL else "подписка"
            
            expired_text = (
                f"❌ **{status_text.capitalize()} истек**\\n\\n"
                f"📅 Дата окончания: {format_datetime_for_user(subscription.end_date)}\\n\\n"
                f"🔒 Доступ к функциям бота ограничен:\\n"
                f"• Общение с виртуальной девушкой недоступно\\n"
                f"• Создание профилей заблокировано\\n"
                f"• История разговоров сохранена\\n\\n"
                f"💎 **Восстановите доступ:**\\n"
                f"• Выберите подходящий план подписки\\n"
                f"• Получите скидку до 33% на длительные планы\\n"
                f"• Мгновенная активация после оплаты\\n\\n"
                f"🎁 Ваши данные и история сохранены!"
            )
            
            # Получаем информацию о подписке для клавиатуры
            subscription_info = await SubscriptionService.get_subscription_info(session, user.id)
            keyboard = get_subscription_keyboard(subscription_info)
            
            await bot.send_message(
                chat_id=user.telegram_id,
                text=expired_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            
            # Обновляем статус подписки на истекшую
            subscription.status = SubscriptionStatus.EXPIRED
            
            # Обновляем время отправки уведомления
            user.last_expired_notification_sent = get_current_utc_time()
            await session.commit()
            
            logger.info(f"Expired notification sent to user {user.telegram_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending expired notification to user {user.telegram_id}: {e}")
            return False
    
    @staticmethod
    async def check_and_send_notifications(bot) -> dict:
        """Основная функция проверки и отправки уведомлений"""
        if not settings.enable_subscription_notifications:
            logger.info("Subscription notifications are disabled")
            return {"expiry_warnings": 0, "expired_notifications": 0, "errors": 0}
        
        stats = {
            "expiry_warnings": 0,
            "expired_notifications": 0,
            "errors": 0
        }
        
        try:
            async with db_service.async_session() as session:
                # Проверяем истекающие подписки
                expiring_users = await NotificationService.get_users_with_expiring_subscriptions(session)
                
                for user, subscription in expiring_users:
                    success = await NotificationService.send_expiry_warning_notification(
                        user, subscription, bot, session
                    )
                    if success:
                        stats["expiry_warnings"] += 1
                    else:
                        stats["errors"] += 1
                
                # Проверяем истекшие подписки
                expired_users = await NotificationService.get_users_with_expired_subscriptions(session)
                
                for user, subscription in expired_users:
                    success = await NotificationService.send_expired_notification(
                        user, subscription, bot, session
                    )
                    if success:
                        stats["expired_notifications"] += 1
                    else:
                        stats["errors"] += 1
                
                logger.info(f"Notification check completed: {stats}")
                return stats
                
        except Exception as e:
            logger.error(f"Error in notification check: {e}")
            stats["errors"] += 1
            return stats