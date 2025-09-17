from sqlalchemy import Column, Integer, String, Numeric, Boolean, Text
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin
from enum import Enum
from decimal import Decimal
import json

class PlanType(str, Enum):
    TRIAL = "trial"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"

class SubscriptionPlan(Base, TimestampMixin):
    __tablename__ = "subscription_plans"
    
    name = Column(String(100), nullable=False)  # Название плана
    plan_type = Column(String(20), nullable=False)  # Тип плана
    duration_days = Column(Integer, nullable=False)  # Длительность в днях
    price = Column(Numeric(10, 2), nullable=False)  # Цена в рублях
    currency = Column(String(3), default="RUB")
    description = Column(Text, nullable=True)  # Описание плана
    features = Column(Text, nullable=True)  # JSON с особенностями плана
    is_active = Column(Boolean, default=True)  # Активен ли план
    discount_percentage = Column(Integer, default=0)  # Процент скидки
    is_popular = Column(Boolean, default=False)  # Популярный план (для выделения в UI)
    
    # Relationships
    subscriptions = relationship("Subscription", back_populates="plan")
    
    def __repr__(self):
        return f"<SubscriptionPlan(name={self.name}, price={self.price})>"
    
    @property
    def price_per_month(self) -> Decimal:
        """Цена за месяц для сравнения планов"""
        return self.price / (Decimal(self.duration_days) / Decimal(30))
    
    @property
    def savings_percentage(self) -> int:
        """Процент экономии по сравнению с месячным планом"""
        if self.plan_type == PlanType.MONTHLY:
            return 0
        
        # Базовая цена за месяц (299 рублей)
        base_monthly_price = Decimal("299")
        monthly_equivalent = self.price_per_month
        
        if monthly_equivalent < base_monthly_price:
            savings = ((base_monthly_price - monthly_equivalent) / base_monthly_price) * Decimal(100)
            return int(savings)
        return 0
    
    def get_features_list(self) -> list:
        """Получение списка особенностей плана"""
        if self.features:
            try:
                return json.loads(self.features)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_features_list(self, features: list):
        """Установка списка особенностей плана"""
        self.features = json.dumps(features, ensure_ascii=False)