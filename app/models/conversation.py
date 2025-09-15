from sqlalchemy import Column, Integer, ForeignKey, Text, String, Boolean
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    girlfriend_profile_id = Column(Integer, ForeignKey("girlfriend_profiles.id"), nullable=False)
    message_type = Column(String(20), nullable=False)  # 'user' или 'assistant'
    content = Column(Text, nullable=False)
    is_deleted = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    girlfriend_profile = relationship("GirlfriendProfile", back_populates="conversations")
    
    def __repr__(self):
        return f"<Conversation(user_id={self.user_id}, type={self.message_type})>"