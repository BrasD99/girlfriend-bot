from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models import Subscription, User, SubscriptionStatus, SubscriptionPlan
from datetime import datetime, timedelta, timezone
from config.settings import settings
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def get_current_utc_time():
    """Получение текущего времени в UTC с timezone"""
    return datetime.now(timezone.utc)


class SubscriptionService:
    @staticmethod
    async def get_active_subscription(session: AsyncSession, user_id: int) -> Optional[Subscription]:
        """Получение активной подписки пользователя"""
        result = await session.execute(
            select(Subscription)
            .where(
                and_(
                    Subscription.user_id == user_id,
                    Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]),
                    Subscription.end_date > get_current_utc_time()
                )
            )
            .order_by(Subscription.end_date.desc())
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def create_trial_subscription(session: AsyncSession, user: User) -> Subscription:
        """Создание пробной подписки"""
        start_date = get_current_utc_time()
        end_date = start_date + timedelta(days=settings.trial_days)
        
        subscription = Subscription(
            user_id=user.id,
            status=SubscriptionStatus.TRIAL,
            start_date=start_date,
            end_date=end_date
        )
        
        session.add(subscription)
        await session.commit()
        await session.refresh(subscription)
        
        logger.info(f"Created trial subscription for user: {user.telegram_id}")
        return subscription
    
    @staticmethod
    async def create_paid_subscription(
        session: AsyncSession, 
        user: User, 
        plan: SubscriptionPlan,
        payment_id: str
    ) -> Subscription:
        """Создание платной подписки"""
        start_date = get_current_utc_time()
        end_date = start_date + timedelta(days=plan.duration_days)
        
        subscription = Subscription(
            user_id=user.id,
            plan_id=plan.id,
            status=SubscriptionStatus.ACTIVE,
            start_date=start_date,
            end_date=end_date,
            payment_id=payment_id,
            is_auto_renewal=True
        )
        
        session.add(subscription)
        await session.commit()
        await session.refresh(subscription)
        
        logger.info(f"Created paid subscription for user: {user.telegram_id}")
        return subscription
    
    @staticmethod
    async def extend_subscription(
        session: AsyncSession, 
        subscription: Subscription, 
        days: int = 30
    ) -> Subscription:
        """Продление подписки"""
        if subscription.end_date < get_current_utc_time():
            # Если подписка уже истекла, начинаем с текущего времени
            subscription.end_date = get_current_utc_time() + timedelta(days=days)
        else:
            # Если подписка еще активна, добавляем дни к текущей дате окончания
            subscription.end_date += timedelta(days=days)
        
        subscription.status = SubscriptionStatus.ACTIVE
        await session.commit()
        await session.refresh(subscription)
        
        logger.info(f"Extended subscription for user_id: {subscription.user_id}")
        return subscription
    
    @staticmethod
    async def cancel_subscription(session: AsyncSession, subscription: Subscription) -> Subscription:
        """Отмена подписки"""
        subscription.status = SubscriptionStatus.CANCELLED
        subscription.is_auto_renewal = False
        await session.commit()
        await session.refresh(subscription)
        
        logger.info(f"Cancelled subscription for user_id: {subscription.user_id}")
        return subscription
    
    @staticmethod
    async def is_user_subscribed(session: AsyncSession, user_id: int) -> bool:
        """Проверка, есть ли у пользователя активная подписка"""
        subscription = await SubscriptionService.get_active_subscription(session, user_id)
        return subscription is not None
    
    @staticmethod
    async def get_subscription_info(session: AsyncSession, user_id: int) -> dict:
        """Получение информации о подписке пользователя"""
        subscription = await SubscriptionService.get_active_subscription(session, user_id)
        
        if not subscription:
            return {
                "has_subscription": False,
                "status": None,
                "end_date": None,
                "days_left": 0
            }
        
        days_left = (subscription.end_date - get_current_utc_time()).days
        
        return {
            "has_subscription": True,
            "status": subscription.status,
            "end_date": subscription.end_date,
            "days_left": max(0, days_left),
            "is_trial": subscription.status == SubscriptionStatus.TRIAL
        }