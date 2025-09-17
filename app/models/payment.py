from sqlalchemy import Column, Integer, ForeignKey, String, Numeric, DateTime, Boolean
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin
from enum import Enum

class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    CANCELLED = "cancelled"
    FAILED = "failed"

class Payment(Base, TimestampMixin):
    __tablename__ = "payments"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    yookassa_payment_id = Column(String(255), unique=True, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="RUB")
    status = Column(String(20), default=PaymentStatus.PENDING)
    description = Column(String(255), nullable=True)
    confirmation_url = Column(String(500), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="payments")
    
    def __repr__(self):
        return f"<Payment(yookassa_payment_id={self.yookassa_payment_id}, status={self.status})>"