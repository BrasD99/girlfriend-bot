from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from app.models import Conversation
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

class ConversationService:
    @staticmethod
    async def save_message(
        session: AsyncSession,
        user_id: int,
        girlfriend_profile_id: int,
        message_type: str,  # 'user' или 'assistant'
        content: str
    ) -> Conversation:
        """Сохранение сообщения в историю разговора"""
        conversation = Conversation(
            user_id=user_id,
            girlfriend_profile_id=girlfriend_profile_id,
            message_type=message_type,
            content=content
        )
        
        session.add(conversation)
        await session.commit()
        await session.refresh(conversation)
        
        return conversation
    
    @staticmethod
    async def get_conversation_history(
        session: AsyncSession,
        user_id: int,
        girlfriend_profile_id: int,
        limit: int = 20
    ) -> List[Conversation]:
        """Получение истории разговора"""
        result = await session.execute(
            select(Conversation)
            .where(
                and_(
                    Conversation.user_id == user_id,
                    Conversation.girlfriend_profile_id == girlfriend_profile_id,
                    Conversation.is_deleted == False
                )
            )
            .order_by(desc(Conversation.created_at))
            .limit(limit)
        )
        
        conversations = result.scalars().all()
        return list(reversed(conversations))  # Возвращаем в хронологическом порядке
    
    @staticmethod
    async def get_recent_context(
        session: AsyncSession,
        user_id: int,
        girlfriend_profile_id: int,
        limit: int = 10
    ) -> str:
        """Получение недавнего контекста для AI"""
        conversations = await ConversationService.get_conversation_history(
            session, user_id, girlfriend_profile_id, limit
        )
        
        context_parts = []
        for conv in conversations:
            role = "Пользователь" if conv.message_type == "user" else "Девушка"
            context_parts.append(f"{role}: {conv.content}")
        
        return "\n".join(context_parts)
    
    @staticmethod
    async def clear_conversation_history(
        session: AsyncSession,
        user_id: int,
        girlfriend_profile_id: Optional[int] = None
    ) -> int:
        """Очистка истории разговора"""
        query = select(Conversation).where(
            and_(
                Conversation.user_id == user_id,
                Conversation.is_deleted == False
            )
        )
        
        if girlfriend_profile_id:
            query = query.where(Conversation.girlfriend_profile_id == girlfriend_profile_id)
        
        result = await session.execute(query)
        conversations = result.scalars().all()
        
        count = 0
        for conv in conversations:
            conv.is_deleted = True
            count += 1
        
        await session.commit()
        logger.info(f"Cleared {count} messages for user {user_id}")
        return count
    
    @staticmethod
    async def get_conversation_stats(
        session: AsyncSession,
        user_id: int,
        girlfriend_profile_id: int
    ) -> dict:
        """Получение статистики разговора"""
        result = await session.execute(
            select(Conversation)
            .where(
                and_(
                    Conversation.user_id == user_id,
                    Conversation.girlfriend_profile_id == girlfriend_profile_id,
                    Conversation.is_deleted == False
                )
            )
        )
        
        conversations = result.scalars().all()
        
        user_messages = sum(1 for conv in conversations if conv.message_type == "user")
        assistant_messages = sum(1 for conv in conversations if conv.message_type == "assistant")
        
        return {
            "total_messages": len(conversations),
            "user_messages": user_messages,
            "assistant_messages": assistant_messages,
            "first_message_date": conversations[0].created_at if conversations else None,
            "last_message_date": conversations[-1].created_at if conversations else None
        }