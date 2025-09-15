from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models import GirlfriendProfile, User
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class GirlfriendService:
    @staticmethod
    async def create_girlfriend_profile(
        session: AsyncSession,
        user: User,
        name: str,
        age: Optional[int] = None,
        personality: Optional[str] = None,
        appearance: Optional[str] = None,
        interests: Optional[str] = None,
        background: Optional[str] = None,
        communication_style: Optional[str] = None
    ) -> GirlfriendProfile:
        """Создание профиля девушки"""
        # Деактивируем все предыдущие профили пользователя
        await GirlfriendService.deactivate_all_profiles(session, user.id)
        
        profile = GirlfriendProfile(
            user_id=user.id,
            name=name,
            age=age,
            personality=personality,
            appearance=appearance,
            interests=interests,
            background=background,
            communication_style=communication_style,
            is_active=True
        )
        
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
        
        logger.info(f"Created girlfriend profile '{name}' for user: {user.telegram_id}")
        return profile
    
    @staticmethod
    async def get_active_profile(session: AsyncSession, user_id: int) -> Optional[GirlfriendProfile]:
        """Получение активного профиля девушки пользователя"""
        result = await session.execute(
            select(GirlfriendProfile)
            .where(
                and_(
                    GirlfriendProfile.user_id == user_id,
                    GirlfriendProfile.is_active == True
                )
            )
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_user_profiles(session: AsyncSession, user_id: int) -> List[GirlfriendProfile]:
        """Получение всех профилей пользователя"""
        result = await session.execute(
            select(GirlfriendProfile)
            .where(GirlfriendProfile.user_id == user_id)
            .order_by(GirlfriendProfile.created_at.desc())
        )
        return result.scalars().all()
    
    @staticmethod
    async def activate_profile(session: AsyncSession, profile_id: int, user_id: int) -> bool:
        """Активация профиля девушки"""
        # Сначала деактивируем все профили пользователя
        await GirlfriendService.deactivate_all_profiles(session, user_id)
        
        # Затем активируем выбранный профиль
        result = await session.execute(
            select(GirlfriendProfile)
            .where(
                and_(
                    GirlfriendProfile.id == profile_id,
                    GirlfriendProfile.user_id == user_id
                )
            )
        )
        profile = result.scalar_one_or_none()
        
        if profile:
            profile.is_active = True
            await session.commit()
            logger.info(f"Activated profile {profile_id} for user {user_id}")
            return True
        
        return False
    
    @staticmethod
    async def deactivate_all_profiles(session: AsyncSession, user_id: int):
        """Деактивация всех профилей пользователя"""
        result = await session.execute(
            select(GirlfriendProfile)
            .where(
                and_(
                    GirlfriendProfile.user_id == user_id,
                    GirlfriendProfile.is_active == True
                )
            )
        )
        profiles = result.scalars().all()
        
        for profile in profiles:
            profile.is_active = False
        
        await session.commit()
    
    @staticmethod
    async def update_profile(
        session: AsyncSession,
        profile_id: int,
        user_id: int,
        **kwargs
    ) -> Optional[GirlfriendProfile]:
        """Обновление профиля девушки"""
        result = await session.execute(
            select(GirlfriendProfile)
            .where(
                and_(
                    GirlfriendProfile.id == profile_id,
                    GirlfriendProfile.user_id == user_id
                )
            )
        )
        profile = result.scalar_one_or_none()
        
        if profile:
            for key, value in kwargs.items():
                if hasattr(profile, key) and value is not None:
                    setattr(profile, key, value)
            
            await session.commit()
            await session.refresh(profile)
            logger.info(f"Updated profile {profile_id} for user {user_id}")
        
        return profile
    
    @staticmethod
    async def update_profile_field(
        session: AsyncSession,
        profile_id: int,
        field_name: str,
        field_value
    ) -> Optional[GirlfriendProfile]:
        """Обновление одного поля профиля девушки"""
        result = await session.execute(
            select(GirlfriendProfile)
            .where(GirlfriendProfile.id == profile_id)
        )
        profile = result.scalar_one_or_none()
        
        if profile and hasattr(profile, field_name):
            setattr(profile, field_name, field_value)
            await session.commit()
            await session.refresh(profile)
            logger.info(f"Updated field '{field_name}' for profile {profile_id}")
        
        return profile
    
    @staticmethod
    async def delete_profile(session: AsyncSession, profile_id: int, user_id: int) -> bool:
        """Удаление профиля девушки"""
        result = await session.execute(
            select(GirlfriendProfile)
            .where(
                and_(
                    GirlfriendProfile.id == profile_id,
                    GirlfriendProfile.user_id == user_id
                )
            )
        )
        profile = result.scalar_one_or_none()
        
        if profile:
            await session.delete(profile)
            await session.commit()
            logger.info(f"Deleted profile {profile_id} for user {user_id}")
            return True
        
        return False