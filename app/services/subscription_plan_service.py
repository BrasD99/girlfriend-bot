from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import SubscriptionPlan, PlanType
from typing import List, Optional
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class SubscriptionPlanService:
    @staticmethod
    async def get_all_active_plans(session: AsyncSession) -> List[SubscriptionPlan]:
        """Получение всех активных планов подписки"""
        result = await session.execute(
            select(SubscriptionPlan)
            .where(SubscriptionPlan.is_active == True)
            .order_by(SubscriptionPlan.duration_days)
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_plan_by_id(session: AsyncSession, plan_id: int) -> Optional[SubscriptionPlan]:
        """Получение плана по ID"""
        result = await session.execute(
            select(SubscriptionPlan)
            .where(SubscriptionPlan.id == plan_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_plan_by_type(session: AsyncSession, plan_type: PlanType) -> Optional[SubscriptionPlan]:
        """Получение плана по типу"""
        result = await session.execute(
            select(SubscriptionPlan)
            .where(
                SubscriptionPlan.plan_type == plan_type,
                SubscriptionPlan.is_active == True
            )
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def create_default_plans(session: AsyncSession) -> List[SubscriptionPlan]:
        """Создание планов по умолчанию"""
        plans_data = [
            {
                "name": "Месячная подписка",
                "plan_type": PlanType.MONTHLY,
                "duration_days": 30,
                "price": Decimal("299"),
                "description": "Базовый месячный план",
                "features": [
                    "Неограниченное общение",
                    "Создание профилей",
                    "История разговоров",
                    "Поддержка 24/7"
                ],
                "is_popular": False
            },
            {
                "name": "Квартальная подписка",
                "plan_type": PlanType.QUARTERLY,
                "duration_days": 90,
                "price": Decimal("799"),  # 266₽/месяц, экономия 11%
                "description": "Подписка на 3 месяца со скидкой",
                "features": [
                    "Неограниченное общение",
                    "Создание профилей",
                    "История разговоров",
                    "Поддержка 24/7",
                    "Экономия 11%"
                ],
                "discount_percentage": 11,
                "is_popular": True
            },
            {
                "name": "Годовая подписка",
                "plan_type": PlanType.YEARLY,
                "duration_days": 365,
                "price": Decimal("2399"),  # 199₽/месяц, экономия 33%
                "description": "Лучшее предложение! Годовая подписка",
                "features": [
                    "Неограниченное общение",
                    "Создание профилей",
                    "История разговоров",
                    "Поддержка 24/7",
                    "Приоритетная поддержка",
                    "Эксклюзивные функции",
                    "Экономия 33%"
                ],
                "discount_percentage": 33,
                "is_popular": False
            }
        ]
        
        created_plans = []
        for plan_data in plans_data:
            # Проверяем, существует ли уже план такого типа
            existing_plan = await SubscriptionPlanService.get_plan_by_type(
                session, plan_data["plan_type"]
            )
            
            if not existing_plan:
                plan = SubscriptionPlan(
                    name=plan_data["name"],
                    plan_type=plan_data["plan_type"],
                    duration_days=plan_data["duration_days"],
                    price=plan_data["price"],
                    description=plan_data["description"],
                    discount_percentage=plan_data.get("discount_percentage", 0),
                    is_popular=plan_data.get("is_popular", False)
                )
                
                plan.set_features_list(plan_data["features"])
                
                session.add(plan)
                created_plans.append(plan)
                
                logger.info(f"Created subscription plan: {plan_data['name']}")
        
        if created_plans:
            await session.commit()
            for plan in created_plans:
                await session.refresh(plan)
        
        return created_plans
    
    @staticmethod
    async def initialize_plans_if_needed(session: AsyncSession):
        """Инициализация планов, если их нет в базе"""
        existing_plans = await SubscriptionPlanService.get_all_active_plans(session)
        
        if not existing_plans:
            logger.info("No subscription plans found, creating default plans...")
            await SubscriptionPlanService.create_default_plans(session)
            logger.info("Default subscription plans created successfully")
    
    @staticmethod
    def format_plan_info(plan: SubscriptionPlan) -> str:
        """Форматирование информации о плане для отображения"""
        try:
            features = plan.get_features_list()
            features_text = "\n".join([f"• {feature}" for feature in features])
            
            price_per_month = plan.price_per_month
            savings = plan.savings_percentage
            
            info_parts = [
                f"💎 **{plan.name}**",
                f"💰 Цена: {plan.price}₽",
                f"📅 Период: {plan.duration_days} дней"
            ]
            
            if plan.plan_type != PlanType.MONTHLY:
                info_parts.append(f"📊 {float(price_per_month):.0f}₽/месяц")
                
            if savings > 0:
                info_parts.append(f"🎉 Экономия: {savings}%")
            
            if plan.is_popular:
                info_parts.append("⭐ **ПОПУЛЯРНЫЙ ВЫБОР**")
            
            info_parts.append(f"\n**Возможности:**\n{features_text}")
            
            return "\n".join(info_parts)
        except Exception as e:
            logger.error(f"Error formatting plan info for plan {plan.id}: {e}")
            return f"💎 **{plan.name}**\n💰 Цена: {plan.price}₽\n📅 Период: {plan.duration_days} дней"
    
    @staticmethod
    def get_plan_emoji(plan: SubscriptionPlan) -> str:
        """Получение эмодзи для плана"""
        emoji_map = {
            PlanType.MONTHLY: "📅",
            PlanType.QUARTERLY: "📈", 
            PlanType.YEARLY: "🏆"
        }
        return emoji_map.get(plan.plan_type, "💎")