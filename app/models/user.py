from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, Integer
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"
    
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    language_code = Column(String(10), default="ru")
    is_active = Column(Boolean, default=True)
    trial_used = Column(Boolean, default=False)
    trial_start_date = Column(DateTime(timezone=True), nullable=True)
    
    # Notification tracking
    last_expiry_notification_sent = Column(DateTime(timezone=True), nullable=True)
    last_expired_notification_sent = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    subscriptions = relationship("Subscription", back_populates="user")
    girlfriend_profiles = relationship("GirlfriendProfile", back_populates="user")
    conversations = relationship("Conversation", back_populates="user")
    payments = relationship("Payment", back_populates="user")
    
    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, username={self.username})>"