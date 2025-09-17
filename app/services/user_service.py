from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models import User
from datetime import datetime, timezone
from typing import Optional
import logging

logger = logging.getLogger(__name__)

def get_current_utc_time():
    """Получение текущего времени в UTC с timezone"""
    return datetime.now(timezone.utc)

class UserService:
    @staticmethod
    async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> Optional[User]:
        """Получение пользователя по Telegram ID"""
        result = await session.execute(
            select(User)
            .options(
                selectinload(User.subscriptions),
                selectinload(User.girlfriend_profiles)
            )
            .where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def create_user(
        session: AsyncSession,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language_code: str = "ru"
    ) -> User:
        """Создание нового пользователя"""
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code
        )
        
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        logger.info(f"Created new user: {telegram_id}")
        return user
    
    @staticmethod
    async def get_or_create_user(
        session: AsyncSession,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language_code: str = "ru"
    ) -> User:
        """Получение существующего пользователя или создание нового"""
        user = await UserService.get_user_by_telegram_id(session, telegram_id)
        
        if not user:
            user = await UserService.create_user(
                session, telegram_id, username, first_name, last_name, language_code
            )
        else:
            # Обновляем информацию о пользователе
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            user.language_code = language_code
            await session.commit()
        
        return user
    
    @staticmethod
    async def start_trial(session: AsyncSession, user: User) -> bool:
        """Запуск пробного периода для пользователя"""
        if user.trial_used:
            return False
        
        user.trial_used = True
        user.trial_start_date = get_current_utc_time()
        await session.commit()
        
        logger.info(f"Started trial for user: {user.telegram_id}")
        return True
    
    @staticmethod
    async def update_user(session: AsyncSession, user: User, **kwargs) -> User:
        """Обновление данных пользователя"""
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        await session.commit()
        await session.refresh(user)
        return user