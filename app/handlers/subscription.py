from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from app.services.database import db_service
from app.services.user_service import UserService
from app.services.subscription_service import SubscriptionService
from app.services.subscription_plan_service import SubscriptionPlanService
from app.services.payment_service import PaymentService
from app.utils.keyboards import (
    get_subscription_keyboard, get_confirmation_keyboard,
    get_subscription_plans_keyboard, get_plan_details_keyboard
)
from app.utils.decorators import user_required, error_handler
from app.utils.helpers import format_subscription_info, safe_edit_message
from app.utils.states import Payment as PaymentState
from app.models import Payment
from config.settings import settings
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("subscription"))
@router.message(F.text == "💎 Подписка")
@error_handler
@user_required
async def subscription_menu(message: types.Message, user):
    """Меню управления подпиской"""
    async with db_service.async_session() as session:
        subscription_info = await SubscriptionService.get_subscription_info(session, user.id)
    
    text = format_subscription_info(subscription_info)
    keyboard = get_subscription_keyboard(subscription_info["has_subscription"])
    
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "subscription_info")
@error_handler
@user_required
async def subscription_info_callback(callback: types.CallbackQuery, user):
    """Подробная информация о подписке"""
    async with db_service.async_session() as session:
        subscription_info = await SubscriptionService.get_subscription_info(session, user.id)
    
    text = format_subscription_info(subscription_info)
    
    # Безопасное редактирование сообщения
    was_edited = await safe_edit_message(callback.message, text, callback.message.reply_markup)
    
    if was_edited:
        await callback.answer("📊 Информация обновлена")
    else:
        await callback.answer("📊 Информация актуальна")


@router.callback_query(F.data == "activate_trial")
@error_handler
@user_required
async def activate_trial_callback(callback: types.CallbackQuery, user):
    """Активация пробного периода"""
    async with db_service.async_session() as session:
        if user.trial_used:
            await callback.answer(
                "❌ Вы уже использовали пробный период",
                show_alert=True
            )
            return
        
        # Проверяем, нет ли уже активной подписки
        if await SubscriptionService.is_user_subscribed(session, user.id):
            await callback.answer(
                "❌ У вас уже есть активная подписка",
                show_alert=True
            )
            return
        
        # Активируем пробный период
        await UserService.start_trial(session, user)
        await SubscriptionService.create_trial_subscription(session, user)
        
        success_text = (
            "🎉 Пробный период активирован!\n\n"
            f"✅ Вам доступны все функции бота на {settings.trial_days} дней\n"
            "💬 Можете начать общение с девушкой\n"
            "👤 Создайте профиль в соответствующем разделе\n\n"
            "Приятного использования! 💕"
        )
        
        await callback.message.edit_text(
            success_text,
            reply_markup=get_subscription_keyboard(True)
        )
        await callback.answer("🎁 Пробный период активирован!")


@router.callback_query(F.data == "buy_subscription")
@error_handler
@user_required
async def buy_subscription_callback(callback: types.CallbackQuery, state: FSMContext, user):
    """Покупка подписки"""
    async with db_service.async_session() as session:
        try:
            # Создаем платеж
            payment = await PaymentService.create_payment(
                session,
                user,
                Decimal(settings.subscription_price),
                "Подписка на месяц"
            )
            
            # Сохраняем ID платежа в состоянии
            await state.set_state(PaymentState.waiting_for_payment)
            await state.update_data(payment_id=payment.id)
            
            payment_text = (
                f"💳 **Оплата подписки**\n\n"
                f"💰 Сумма: {settings.subscription_price}₽\n"
                f"📅 Период: 1 месяц\n"
                f"🔄 Автопродление: Да\n\n"
                f"Нажмите кнопку 'Оплатить' для перехода к оплате."
            )
            
            from app.utils.keyboards import get_payment_keyboard
            keyboard = get_payment_keyboard(payment.confirmation_url)
            
            await callback.message.edit_text(
                payment_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error creating payment: {e}")
            await callback.answer(
                "❌ Ошибка при создании платежа. Попробуйте позже.",
                show_alert=True
            )


@router.callback_query(F.data == "cancel_payment")
@error_handler
async def cancel_payment_callback(callback: types.CallbackQuery, state: FSMContext):
    """Отмена платежа"""
    await state.clear()
    
    cancel_text = (
        "❌ Оплата отменена\n\n"
        "Вы можете вернуться к оплате в любое время через меню подписки."
    )
    
    await callback.message.edit_text(
        cancel_text,
        reply_markup=get_subscription_keyboard(False)
    )
    await callback.answer("Оплата отменена")


@router.callback_query(F.data == "extend_subscription")
@error_handler
@user_required
async def extend_subscription_callback(callback: types.CallbackQuery, state: FSMContext, user):
    """Продление подписки"""
    # Аналогично покупке подписки
    await buy_subscription_callback(callback, state, user)


@router.callback_query(F.data == "cancel_subscription")
@error_handler
@user_required
async def cancel_subscription_callback(callback: types.CallbackQuery, user):
    """Отмена подписки"""
    confirmation_text = (
        "❓ Вы уверены, что хотите отменить подписку?\n\n"
        "⚠️ После отмены:\n"
        "• Автопродление будет отключено\n"
        "• Доступ сохранится до конца текущего периода\n"
        "• Вы сможете возобновить подписку в любое время"
    )
    
    keyboard = get_confirmation_keyboard("subscription_cancel")
    
    await callback.message.edit_text(
        confirmation_text,
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_subscription_cancel")
@error_handler
@user_required
async def confirm_cancel_subscription(callback: types.CallbackQuery, user):
    """Подтверждение отмены подписки"""
    async with db_service.async_session() as session:
        subscription = await SubscriptionService.get_active_subscription(session, user.id)
        
        if subscription:
            await SubscriptionService.cancel_subscription(session, subscription)
            
            # Получаем обновленную информацию о подписке
            subscription_info = await SubscriptionService.get_subscription_info(session, user.id)
            text = format_subscription_info(subscription_info)
            keyboard = get_subscription_keyboard(subscription_info["has_subscription"])
            
            await callback.message.edit_text(
                text,
                reply_markup=keyboard
            )
            await callback.answer("Подписка отменена")
        else:
            await callback.answer("❌ Активная подписка не найдена", show_alert=True)


@router.callback_query(F.data == "cancel_subscription_cancel")
@error_handler
async def cancel_subscription_cancel(callback: types.CallbackQuery):
    """Отмена отмены подписки"""
    await callback.message.edit_text(
        "Отмена подписки отменена 😊",
        reply_markup=get_subscription_keyboard(True)
    )
    await callback.answer()


@router.callback_query(F.data == "view_plans")
@error_handler
@user_required
async def view_plans_callback(callback: types.CallbackQuery, user):
    """Просмотр доступных планов подписки"""
    async with db_service.async_session() as session:
        # Инициализируем планы, если их нет
        await SubscriptionPlanService.initialize_plans_if_needed(session)
        
        # Получаем все активные планы
        plans = await SubscriptionPlanService.get_all_active_plans(session)
        
        if not plans:
            await callback.answer("❌ Планы подписок не найдены", show_alert=True)
            return
        
        plans_text = "💳 **Выберите план подписки:**\n\n"
        
        for plan in plans:
            plan_info = SubscriptionPlanService.format_plan_info(plan)
            plans_text += f"{plan_info}\n\n"
            plans_text += "---\n\n"
        
        keyboard = get_subscription_plans_keyboard(plans)
        
        await callback.message.edit_text(
            plans_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer()


@router.callback_query(F.data.startswith("buy_plan_"))
@error_handler
@user_required
async def buy_plan_callback(callback: types.CallbackQuery, state: FSMContext, user):
    """Покупка конкретного плана"""
    plan_id = int(callback.data.split("_")[-1])
    
    async with db_service.async_session() as session:
        plan = await SubscriptionPlanService.get_plan_by_id(session, plan_id)
        
        if not plan:
            await callback.answer("❌ План не найден", show_alert=True)
            return
        
        plan_details = SubscriptionPlanService.format_plan_info(plan)
        
        details_text = (
            f"💳 **Подробности плана:**\n\n"
            f"{plan_details}\n\n"
            f"Подтвердите покупку:"
        )
        
        keyboard = get_plan_details_keyboard(plan_id)
        
        await callback.message.edit_text(
            details_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer()


@router.callback_query(F.data.startswith("confirm_buy_plan_"))
@error_handler
@user_required
async def confirm_buy_plan_callback(callback: types.CallbackQuery, state: FSMContext, user):
    """Подтверждение покупки плана"""
    plan_id = int(callback.data.split("_")[-1])
    
    async with db_service.async_session() as session:
        plan = await SubscriptionPlanService.get_plan_by_id(session, plan_id)
        
        if not plan:
            await callback.answer("❌ План не найден", show_alert=True)
            return
        
        try:
            # Создаем платеж
            payment = await PaymentService.create_payment(
                session,
                user,
                plan.price,
                f"Подписка: {plan.name}",
                plan.id
            )
            
            # Сохраняем ID плана и платежа в состоянии
            await state.set_state(PaymentState.waiting_for_payment)
            await state.update_data(payment_id=payment.id, plan_id=plan.id)
            
            payment_text = (
                f"💳 **Оплата подписки**\n\n"
                f"💸 План: {plan.name}\n"
                f"💰 Сумма: {plan.price}₽\n"
                f"📅 Период: {plan.duration_days} дней\n"
                f"🔄 Автопродление: Да\n\n"
                f"Нажмите кнопку 'Оплатить' для перехода к оплате.\n"
                f"После успешной оплаты подписка будет активирована автоматически."
            )
            
            from app.utils.keyboards import get_payment_keyboard
            keyboard = get_payment_keyboard(payment.confirmation_url)
            
            await callback.message.edit_text(
                payment_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Error creating payment for plan {plan_id}: {e}")
            await callback.answer(
                "❌ Ошибка при создании платежа. Попробуйте позже.",
                show_alert=True
            )


@router.callback_query(F.data == "back_to_subscription")
@error_handler
@user_required
async def back_to_subscription_callback(callback: types.CallbackQuery, user):
    """Возврат к меню подписки"""
    async with db_service.async_session() as session:
        subscription_info = await SubscriptionService.get_subscription_info(session, user.id)
    
    text = format_subscription_info(subscription_info)
    keyboard = get_subscription_keyboard(subscription_info["has_subscription"])
    
    # Безопасное редактирование сообщения
    await safe_edit_message(callback.message, text, keyboard)
    await callback.answer()