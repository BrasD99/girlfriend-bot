from sqlalchemy import Column, Integer, ForeignKey, String, Text, Boolean
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class GirlfriendProfile(Base, TimestampMixin):
    __tablename__ = "girlfriend_profiles"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=True)
    personality = Column(Text, nullable=True)  # Описание характера
    appearance = Column(Text, nullable=True)  # Описание внешности
    interests = Column(Text, nullable=True)   # Интересы и хобби
    background = Column(Text, nullable=True)  # Предыстория
    communication_style = Column(Text, nullable=True)  # Стиль общения
    user_description = Column(Text, nullable=True)  # Описание пользователя для персонализации
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", back_populates="girlfriend_profiles")
    conversations = relationship("Conversation", back_populates="girlfriend_profile")
    
    def __repr__(self):
        return f"<GirlfriendProfile(name={self.name}, user_id={self.user_id})>"
    
    def get_full_prompt(self) -> str:
        """Создает полный промпт для AI на основе характеристик"""
        prompt_parts = [
            f"Ты играешь роль девушки по имени {self.name}."
        ]
        
        if self.age:
            prompt_parts.append(f"Тебе {self.age} лет.")
            
        if self.personality:
            prompt_parts.append(f"Твой характер: {self.personality}")
            
        if self.appearance:
            prompt_parts.append(f"Твоя внешность: {self.appearance}")
            
        if self.interests:
            prompt_parts.append(f"Твои интересы: {self.interests}")
            
        if self.background:
            prompt_parts.append(f"Твоя предыстория: {self.background}")
            
        if self.communication_style:
            prompt_parts.append(f"Стиль общения: {self.communication_style}")
            
        if self.user_description:
            prompt_parts.append(f"Информация о твоем собеседнике: {self.user_description}")
            prompt_parts.append("Учитывай эту информацию в разговоре, находи общие темы и интересы.")
            
        prompt_parts.extend([
            "Общайся естественно, как настоящая девушка.",
            "Отвечай на русском языке.",
            "Будь эмоциональной и живой в общении.",
            "Можешь использовать эмодзи для выражения эмоций.",
            "Не упоминай, что ты искусственный интеллект.",
            "Проявляй интерес к собеседнику и его жизни."
        ])
        
        return " ".join(prompt_parts)