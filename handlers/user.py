from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
import keyboards as kb
from config import config

router = Router()

# ==================== СОСТОЯНИЯ ====================

class BookingStates(StatesGroup):
    choosing_service = State()
    choosing_master = State()
    choosing_date = State()
    choosing_time = State()
    entering_phone = State()
    confirming = State()

# ==================== СТАРТ ====================

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    
    # Сохраняем пользователя
    await db.save_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name
    )
    
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "Я бот для записи на услуги. Выберите действие:",
        reply_markup=kb.main_menu_kb()
    )

# ==================== ЗАПИСЬ НА УСЛУГУ ====================

@router.message(F.text == "📝 Записаться")
async def start_booking(message: Message, state: FSMContext):
    await state.set_state(BookingStates.choosing_service)
    
    await message.answer(
        "💈 Выберите услугу:",
        reply_markup=await kb.services_kb()
    )

@router.callback_query(F.data.startswith("service_"))
async def service_selected(callback: CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split("_")[1])
    service = await db.get_service(service_id)
    
    await state.update_data(
        service_id=service_id,
        service_name=service.name,
        service_price=service.price
    )
    await state.set_state(BookingStates.choosing_master)
    
    await callback.message.edit_text(
        f"✅ Услуга: {service.name} ({service.price}₽)\n\n"
        "👤 Выберите мастера:",
        reply_markup=await kb.masters_kb(service_id)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("master_"))
async def master_selected(callback: CallbackQuery, state: FSMContext):
    master_id = int(callback.data.split("_")[1])
    
    if master_id == 0:
        master_name = "Любой мастер"
    else:
        master = await db.get_master(master_id)
        master_name = master.name
    
    await state.update_data(master_id=master_id, master_name=master_name)
    await state.set_state(BookingStates.choosing_date)
    
    data = await state.get_data()
    
    await callback.message.edit_text(
        f"✅ Услуга: {data['service_name']} ({data['service_price']}₽)\n"
        f"✅ Мастер: {master_name}\n\n"
        "📅 Выберите дату:",
        reply_markup=kb.dates_kb()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("date_"))
async def date_selected(callback: CallbackQuery, state: FSMContext):
    date_str = callback.data.split("_")[1]
    await state.update_data(date=date_str)
    await state.set_state(BookingStates.choosing_time)
    
    data = await state.get_data()
    master_id = data.get('master_id')
    
    # Форматируем дату для отображения
    from datetime import datetime
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    formatted_date = date_obj.strftime('%d.%m.%Y')
    
    await callback.message.edit_text(
        f"✅ Услуга: {data['service_name']} ({data['service_price']}₽)\n"
        f"✅ Мастер: {data['master_name']}\n"
        f"✅ Дата: {formatted_date}\n\n"
        "🕐 Выберите время:",
        reply_markup=await kb.times_kb(date_str, master_id if master_id != 0 else None)
    )
    await callback.answer()

@router.callback_query(F.data == "slot_busy")
async def slot_busy(callback: CallbackQuery):
    await callback.answer("⚠️ Это время уже занято", show_alert=True)

@router.callback_query(F.data.startswith("time_"))
async def time_selected(callback: CallbackQuery, state: FSMContext):
    time_str = callback.data.split("_")[1]
    await state.update_data(time=time_str)
    
    # Проверяем, есть ли телефон пользователя
    phone = await db.get_user_phone(callback.from_user.id)
    
    if phone:
        await state.update_data(phone=phone)
        await state.set_state(BookingStates.confirming)
        await show_confirmation(callback.message, state)
    else:
        await state.set_state(BookingStates.entering_phone)
        await callback.message.answer(
            "📱 Отправьте ваш номер телефона для связи:",
            reply_markup=kb.phone_kb()
        )
    
    await callback.answer()

@router.message(BookingStates.entering_phone, F.contact)
async def phone_received(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    await state.update_data(phone=phone)
    
    # Сохраняем телефон пользователя
    await db.update_user_phone(message.from_user.id, phone)
    
    await state.set_state(BookingStates.confirming)
    await message.answer(
        "✅ Номер сохранён!",
        reply_markup=kb.main_menu_kb()
    )
    await show_confirmation(message, state)

@router.message(BookingStates.entering_phone, F.text)
async def phone_text(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "❌ Запись отменена",
            reply_markup=kb.main_menu_kb()
        )
        return
    
    # Простая валидация телефона
    phone = message.text.replace(" ", "").replace("-", "")
    if phone.startswith("+") and len(phone) >= 11:
        await state.update_data(phone=phone)
        await db.update_user_phone(message.from_user.id, phone)
        await state.set_state(BookingStates.confirming)
        await show_confirmation(message, state)
    else:
        await message.answer(
            "⚠️ Введите корректный номер телефона\n"
            "Пример: +7 999 123 45 67"
        )

async def show_confirmation(message: Message, state: FSMContext):
    data = await state.get_data()
    
    from datetime import datetime
    date_obj = datetime.strptime(data['date'], '%Y-%m-%d')
    formatted_date = date_obj.strftime('%d.%m.%Y')
    
    text = (
        "📋 <b>Проверьте данные записи:</b>\n\n"
        f"💈 Услуга: {data['service_name']}\n"
        f"💰 Стоимость: {data['service_price']}₽\n"
        f"👤 Мастер: {data['master_name']}\n"
        f"📅 Дата: {formatted_date}\n"
        f"🕐 Время: {data['time']}\n"
        f"📱 Телефон: {data['phone']}\n\n"
        "Всё верно?"
    )
    
    await message.answer(text, reply_markup=kb.confirm_kb(), parse_mode="HTML")

@router.callback_query(F.data == "confirm_booking")
async def confirm_booking(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    
    # Создаём запись
    booking_id = await db.create_booking(
        user_id=callback.from_user.id,
        user_name=callback.from_user.full_name,
        user_phone=data['phone'],
        service_id=data['service_id'],
        master_id=data['master_id'] if data['master_id'] != 0 else None,
        date_str=data['date'],
        time_str=data['time']
    )
    
    from datetime import datetime
    date_obj = datetime.strptime(data['date'], '%Y-%m-%d')
    formatted_date = date_obj.strftime('%d.%m.%Y')
    
    await callback.message.edit_text(
        f"✅ <b>Запись создана!</b>\n\n"
        f"📋 Номер записи: #{booking_id}\n"
        f"💈 Услуга: {data['service_name']}\n"
        f"📅 Дата: {formatted_date}\n"
        f"🕐 Время: {data['time']}\n\n"
        "Мы свяжемся с вами для подтверждения.",
        parse_mode="HTML"
    )
    
    # Уведомление админам
    from bot import bot
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"🆕 <b>Новая запись #{booking_id}</b>\n\n"
                f"👤 Клиент: {callback.from_user.full_name}\n"
                f"📱 Телефон: {data['phone']}\n"
                f"💈 Услуга: {data['service_name']}\n"
                f"👤 Мастер: {data['master_name']}\n"
                f"📅 Дата: {formatted_date}\n"
                f"🕐 Время: {data['time']}",
                reply_markup=kb.admin_booking_kb(booking_id),
                parse_mode="HTML"
            )
        except Exception:
            pass
    
    await state.clear()
    await callback.answer("✅ Записано!")

# ==================== НАВИГАЦИЯ НАЗАД ====================

@router.callback_query(F.data == "back_to_services")
async def back_to_services(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BookingStates.choosing_service)
    await callback.message.edit_text(
        "💈 Выберите услугу:",
        reply_markup=await kb.services_kb()
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_masters")
async def back_to_masters(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BookingStates.choosing_master)
    data = await state.get_data()
    
    await callback.message.edit_text(
        f"✅ Услуга: {data['service_name']} ({data['service_price']}₽)\n\n"
        "👤 Выберите мастера:",
        reply_markup=await kb.masters_kb(data['service_id'])
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_dates")
async def back_to_dates(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BookingStates.choosing_date)
    data = await state.get_data()
    
    await callback.message.edit_text(
        f"✅ Услуга: {data['service_name']} ({data['service_price']}₽)\n"
        f"✅ Мастер: {data['master_name']}\n\n"
        "📅 Выберите дату:",
        reply_markup=kb.dates_kb()
    )
    await callback.answer()

@router.callback_query(F.data == "cancel")
async def cancel_booking_process(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Запись отменена")
    await callback.answer()

# ==================== МОИ ЗАПИСИ ====================

@router.message(F.text == "📋 Мои записи")
async def my_bookings(message: Message):
    bookings = await db.get_user_bookings(message.from_user.id)
    
    if not bookings:
        await message.answer("📭 У вас пока нет записей")
        return
    
    from datetime import datetime
    
    text = "📋 <b>Ваши записи:</b>\n\n"
    for booking in bookings:
        service = await db.get_service(booking.service_id)
        master = await db.get_master(booking.master_id) if booking.master_id else None
        
        date_obj = datetime.strptime(booking.date, '%Y-%m-%d')
        formatted_date = date_obj.strftime('%d.%m.%Y')
        
        status_emoji = {
            'pending': '🕐',
            'confirmed': '✅',
            'completed': '✔️',
            'cancelled': '❌'
        }
        
        text += (
            f"{status_emoji.get(booking.status, '❓')} <b>Запись #{booking.id}</b>\n"
            f"   💈 {service.name if service else 'Услуга'}\n"
            f"   👤 {master.name if master else 'Любой мастер'}\n"
            f"   📅 {formatted_date} в {booking.time}\n\n"
        )
    
    await message.answer(
        text,
        reply_markup=kb.my_bookings_kb(bookings),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("cancel_booking_"))
async def cancel_my_booking(callback: CallbackQuery):
    booking_id = int(callback.data.split("_")[2])
    await db.cancel_booking(booking_id)
    
    await callback.message.edit_text(
        f"❌ Запись #{booking_id} отменена"
    )
    await callback.answer("Запись отменена")

# ==================== УСЛУГИ И ЦЕНЫ ====================

@router.message(F.text == "💈 Услуги и цены")
async def show_services(message: Message):
    services = await db.get_services()
    
    text = "💈 <b>Наши услуги:</b>\n\n"
    for service in services:
        text += f"• {service.name} — <b>{service.price}₽</b> ({service.duration} мин)\n"
    
    await message.answer(text, parse_mode="HTML")

# ==================== КОНТАКТЫ ====================

@router.message(F.text == "📞 Контакты")
async def show_contacts(message: Message):
    await message.answer(
        "📞 <b>Наши контакты:</b>\n\n"
        "📍 Адрес: ул. Примерная, д. 1\n"
        "📱 Телефон: +7 (999) 123-45-67\n"
        "🕐 Режим работы: 9:00 - 21:00\n\n"
        "Instagram: @example\n"
        "Мы в VK: vk.com/example",
        parse_mode="HTML"
    )
