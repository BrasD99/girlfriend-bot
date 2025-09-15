from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Payment, User, PaymentStatus
from yookassa import Configuration, Payment as YooKassaPayment
from config.settings import settings
from typing import Optional
from decimal import Decimal
import uuid
import logging

logger = logging.getLogger(__name__)

# Настройка YooKassa
Configuration.account_id = settings.yookassa_shop_id
Configuration.secret_key = settings.yookassa_secret_key


class PaymentService:
    @staticmethod
    async def create_payment(
        session: AsyncSession,
        user: User,
        amount: Decimal,
        description: str = "Подписка на месяц"
    ) -> Payment:
        """Создание платежа через YooKassa"""
        
        # Создаем платеж в YooKassa
        yookassa_payment = YooKassaPayment.create({
            "amount": {
                "value": str(amount),
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": settings.get_payment_return_url()
            },
            "capture": True,
            "description": description,
            "metadata": {
                "user_id": str(user.id),
                "telegram_id": str(user.telegram_id)
            }
        }, uuid.uuid4())
        
        # Сохраняем платеж в базе данных
        payment = Payment(
            user_id=user.id,
            yookassa_payment_id=yookassa_payment.id,
            amount=amount,
            description=description,
            status=PaymentStatus.PENDING,
            confirmation_url=yookassa_payment.confirmation.confirmation_url
        )
        
        session.add(payment)
        await session.commit()
        await session.refresh(payment)
        
        logger.info(f"Created payment {yookassa_payment.id} for user {user.telegram_id}")
        return payment
    
    @staticmethod
    async def get_payment_by_yookassa_id(
        session: AsyncSession,
        yookassa_payment_id: str
    ) -> Optional[Payment]:
        """Получение платежа по ID YooKassa"""
        result = await session.execute(
            select(Payment)
            .where(Payment.yookassa_payment_id == yookassa_payment_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_payment_status(
        session: AsyncSession,
        payment: Payment,
        status: PaymentStatus,
        paid_at: Optional[str] = None
    ) -> Payment:
        """Обновление статуса платежа"""
        payment.status = status
        if paid_at:
            payment.paid_at = paid_at
        
        await session.commit()
        await session.refresh(payment)
        
        logger.info(f"Updated payment {payment.yookassa_payment_id} status to {status}")
        return payment
    
    @staticmethod
    async def check_payment_status(
        session: AsyncSession,
        payment: Payment
    ) -> Payment:
        """Проверка статуса платежа в YooKassa"""
        try:
            yookassa_payment = YooKassaPayment.find_one(payment.yookassa_payment_id)
            
            if yookassa_payment.status == "succeeded":
                payment = await PaymentService.update_payment_status(
                    session, payment, PaymentStatus.SUCCEEDED, yookassa_payment.paid_at
                )
            elif yookassa_payment.status == "canceled":
                payment = await PaymentService.update_payment_status(
                    session, payment, PaymentStatus.CANCELLED
                )
            elif yookassa_payment.status == "failed":
                payment = await PaymentService.update_payment_status(
                    session, payment, PaymentStatus.FAILED
                )
            
        except Exception as e:
            logger.error(f"Error checking payment status: {e}")
        
        return payment
    
    @staticmethod
    async def process_webhook(session: AsyncSession, webhook_data: dict) -> bool:
        """Обработка webhook от YooKassa"""
        try:
            event_type = webhook_data.get("event")
            payment_data = webhook_data.get("object")
            
            if event_type == "payment.succeeded" and payment_data:
                payment_id = payment_data.get("id")
                payment = await PaymentService.get_payment_by_yookassa_id(session, payment_id)
                
                if payment and payment.status == PaymentStatus.PENDING:
                    await PaymentService.update_payment_status(
                        session, payment, PaymentStatus.SUCCEEDED, payment_data.get("paid_at")
                    )
                    return True
            
            elif event_type == "payment.canceled" and payment_data:
                payment_id = payment_data.get("id")
                payment = await PaymentService.get_payment_by_yookassa_id(session, payment_id)
                
                if payment and payment.status == PaymentStatus.PENDING:
                    await PaymentService.update_payment_status(
                        session, payment, PaymentStatus.CANCELLED
                    )
                    return True
            
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
        
        return False