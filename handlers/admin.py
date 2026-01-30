from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
import keyboards as kb
from config import config

router = Router()

# ==================== ФИЛЬТР АДМИНА ====================

class AdminFilter:
    def __call__(self, message: Message) -> bool:
        return message.from_user.id in config.ADMIN_IDS

# ==================== СОСТОЯНИЯ ====================

class AdminStates(StatesGroup):
    adding_service_name = State()
    adding_service_price = State()
    adding_service_duration = State()

# ==================== АДМИН-ПАНЕЛЬ ====================

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("⛔ У вас нет доступа")
        return
    
    await message.answer(
        "👨‍💼 <b>Админ-панель</b>\n\n"
        "Выберите действие:",
        reply_markup=kb.admin_menu_kb(),
        parse_mode="HTML"
    )

@router.message(F.text == "👤 В режим клиента")
async def to_client_mode(message: Message):
    await message.answer(
        "Вы в режиме клиента",
        reply_markup=kb.main_menu_kb()
    )

# ==================== ПРОСМОТР ЗАПИСЕЙ ====================

@router.message(F.text == "📊 Все записи")
async def all_bookings(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:
        return
    
    bookings = await db.get_all_bookings()
    
    if not bookings:
        await message.answer("📭 Записей нет")
        return
    
    from datetime import datetime
    
    text = "📊 <b>Все записи:</b>\n\n"
    for booking in bookings[:20]:  # Последние 20
        service = await db.get_service(booking.service_id)
        
        date_obj = datetime.strptime(booking.date, '%Y-%m-%d')
        formatted_date = date_obj.strftime('%d.%m.%Y')
        
        status_map = {
            'pending': '🕐 Ожидает',
            'confirmed': '✅ Подтверждена',
            'completed': '✔️ Выполнена',
            'cancelled': '❌ Отменена'
        }
        
        text += (
            f"<b>#{booking.id}</b> | {formatted_date} {booking.time}\n"
            f"👤 {booking.user_name} | 📱 {booking.user_phone}\n"
            f"💈 {service.name if service else '-'}\n"
            f"Статус: {status_map.get(booking.status, booking.status)}\n\n"
        )
    
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "📅 Записи на сегодня")
async def today_bookings(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:
        return
    
    from datetime import datetime
    today = datetime.now().strftime('%Y-%m-%d')
    
    bookings = await db.get_all_bookings()
    today_bookings = [b for b in bookings if b.date == today and b.status != 'cancelled']
    
    if not today_bookings:
        await message.answer("📭 На сегодня записей нет")
        return
    
    text = "📅 <b>Записи на сегодня:</b>\n\n"
    for booking in sorted(today_bookings, key=lambda x: x.time):
        service = await db.get_service(booking.service_id)
        master = await db.get_master(booking.master_id) if booking.master_id else None
        
        status_emoji = '✅' if booking.status == 'confirmed' else '🕐'
        
        text += (
            f"{status_emoji} <b>{booking.time}</b> — {booking.user_name}\n"
            f"   📱 {booking.user_phone}\n"
            f"   💈 {service.name if service else '-'}"
            f"{f' ({master.name})' if master else ''}\n\n"
        )
    
    await message.answer(text, parse_mode="HTML")

# ==================== УПРАВЛЕНИЕ ЗАПИСЯМИ ====================

@router.callback_query(F.data.startswith("admin_confirm_"))
async def admin_confirm_booking(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔ Нет доступа")
        return
    
    booking_id = int(callback.data.split("_")[2])
    await db.update_booking_status(booking_id, "confirmed")
    
    # Уведомляем клиента
    booking = await db.get_booking(booking_id)
    if booking:
        from bot import bot
        try:
            from datetime import datetime
            date_obj = datetime.strptime(booking.date, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%d.%m.%Y')
            
            await bot.send_message(
                booking.user_id,
                f"✅ <b>Ваша запись подтверждена!</b>\n\n"
                f"📅 Дата: {formatted_date}\n"
                f"🕐 Время: {booking.time}\n\n"
                f"Ждём вас!",
                parse_mode="HTML"
            )
        except Exception:
            pass
    
    await callback.message.edit_text(
        callback.message.text + "\n\n✅ ПОДТВЕРЖДЕНО",
        parse_mode="HTML"
    )
    await callback.answer("✅ Запись подтверждена")

@router.callback_query(F.data.startswith("admin_cancel_"))
async def admin_cancel_booking(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔ Нет доступа")
        return
    
    booking_id = int(callback.data.split("_")[2])
    await db.update_booking_status(booking_id, "cancelled")
    
    # Уведомляем клиента
    booking = await db.get_booking(booking_id)
    if booking:
        from bot import bot
        try:
            await bot.send_message(
                booking.user_id,
                f"❌ <b>Ваша запись #{booking_id} отменена</b>\n\n"
                "Свяжитесь с нами для уточнения деталей.",
                parse_mode="HTML"
            )
        except Exception:
            pass
    
    await callback.message.edit_text(
        callback.message.text + "\n\n❌ ОТМЕНЕНО",
        parse_mode="HTML"
    )
    await callback.answer("❌ Запись отменена")

@router.callback_query(F.data.startswith("admin_complete_"))
async def admin_complete_booking(callback: CallbackQuery):
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔ Нет доступа")
        return
    
    booking_id = int(callback.data.split("_")[2])
    await db.update_booking_status(booking_id, "completed")
    
    await callback.message.edit_text(
        callback.message.text + "\n\n✔️ ВЫПОЛНЕНО",
        parse_mode="HTML"
    )
    await callback.answer("✔️ Отмечено как выполненное")

# ==================== УПРАВЛЕНИЕ УСЛУГАМИ ====================

@router.message(F.text == "📝 Управление услугами")
async def manage_services(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:
        return
    
    services = await db.get_services(active_only=False)
    
    await message.answer(
        "📝 <b>Управление услугами:</b>\n\n"
        "Нажмите на услугу для редактирования:",
        reply_markup=kb.admin_services_kb(services),
        parse_mode="HTML"
    )

@router.message(F.text == "➕ Добавить услугу")
async def add_service_start(message: Message, state: FSMContext):
    if message.from_user.id not in config.ADMIN_IDS:
        return
    
    await state.set_state(AdminStates.adding_service_name)
    await message.answer(
        "➕ <b>Добавление услуги</b>\n\n"
        "Введите название услуги:",
        parse_mode="HTML"
    )

@router.message(AdminStates.adding_service_name)
async def add_service_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AdminStates.adding_service_price)
    await message.answer("💰 Введите цену (только число):")

@router.message(AdminStates.adding_service_price)
async def add_service_price(message: Message, state: FSMContext):
    try:
        price = int(message.text)
        await state.update_data(price=price)
        await state.set_state(AdminStates.adding_service_duration)
        await message.answer("⏱ Введите длительность в минутах (по умолчанию 60):")
    except ValueError:
        await message.answer("⚠️ Введите число!")

@router.message(AdminStates.adding_service_duration)
async def add_service_duration(message: Message, state: FSMContext):
    try:
        duration = int(message.text) if message.text else 60
    except ValueError:
        duration = 60
    
    data = await state.get_data()
    
    service_id = await db.add_service(data['name'], data['price'], duration)
    
    await message.answer(
        f"✅ Услуга добавлена!\n\n"
        f"ID: {service_id}\n"
        f"Название: {data['name']}\n"
        f"Цена: {data['price']}₽\n"
        f"Длительность: {duration} мин",
        reply_markup=kb.admin_menu_kb()
    )
    await state.clear()
