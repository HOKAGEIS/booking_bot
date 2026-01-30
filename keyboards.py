from aiogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from datetime import datetime, timedelta
from typing import List
from config import config
import database as db

# ==================== ГЛАВНОЕ МЕНЮ ====================

def main_menu_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📝 Записаться"),
        KeyboardButton(text="📋 Мои записи")
    )
    builder.row(
        KeyboardButton(text="💈 Услуги и цены"),
        KeyboardButton(text="📞 Контакты")
    )
    return builder.as_markup(resize_keyboard=True)

def admin_menu_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📊 Все записи"),
        KeyboardButton(text="📅 Записи на сегодня")
    )
    builder.row(
        KeyboardButton(text="➕ Добавить услугу"),
        KeyboardButton(text="📝 Управление услугами")
    )
    builder.row(
        KeyboardButton(text="👤 В режим клиента")
    )
    return builder.as_markup(resize_keyboard=True)

# ==================== УСЛУГИ ====================

async def services_kb() -> InlineKeyboardMarkup:
    services = await db.get_services()
    builder = InlineKeyboardBuilder()
    
    for service in services:
        builder.row(
            InlineKeyboardButton(
                text=f"{service.name} — {service.price}₽",
                callback_data=f"service_{service.id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return builder.as_markup()

# ==================== МАСТЕРА ====================

async def masters_kb(service_id: int) -> InlineKeyboardMarkup:
    masters = await db.get_masters_for_service(service_id)
    builder = InlineKeyboardBuilder()
    
    # Кнопка "любой мастер"
    builder.row(
        InlineKeyboardButton(
            text="👤 Любой мастер",
            callback_data=f"master_0"
        )
    )
    
    for master in masters:
        builder.row(
            InlineKeyboardButton(
                text=f"💇 {master.name}",
                callback_data=f"master_{master.id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_services"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return builder.as_markup()

# ==================== ДАТЫ ====================

def dates_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    today = datetime.now().date()
    
    # Названия дней недели
    days_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    months = ["янв", "фев", "мар", "апр", "май", "июн", 
              "июл", "авг", "сен", "окт", "ноя", "дек"]
    
    buttons = []
    for i in range(config.DAYS_AHEAD):
        date = today + timedelta(days=i)
        day_name = days_names[date.weekday()]
        date_str = f"{date.day} {months[date.month-1]}"
        
        buttons.append(
            InlineKeyboardButton(
                text=f"{day_name}, {date_str}",
                callback_data=f"date_{date.strftime('%Y-%m-%d')}"
            )
        )
    
    # По 2 кнопки в ряд
    for i in range(0, len(buttons), 2):
        if i + 1 < len(buttons):
            builder.row(buttons[i], buttons[i+1])
        else:
            builder.row(buttons[i])
    
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_masters"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return builder.as_markup()

# ==================== ВРЕМЯ ====================

async def times_kb(date_str: str, master_id: int = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    # Получаем занятые слоты
    booked = await db.get_booked_slots(date_str, master_id)
    
    # Генерируем доступные слоты
    buttons = []
    for hour in range(config.WORK_START, config.WORK_END):
        time_str = f"{hour:02d}:00"
        
        # Проверяем, не прошло ли время (если дата сегодня)
        if date_str == datetime.now().strftime('%Y-%m-%d'):
            if hour <= datetime.now().hour:
                continue
        
        if time_str not in booked:
            buttons.append(
                InlineKeyboardButton(
                    text=f"🕐 {time_str}",
                    callback_data=f"time_{time_str}"
                )
            )
        else:
            buttons.append(
                InlineKeyboardButton(
                    text=f"❌ {time_str}",
                    callback_data="slot_busy"
                )
            )
    
    # По 3 кнопки в ряд
    for i in range(0, len(buttons), 3):
        row = buttons[i:i+3]
        builder.row(*row)
    
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_dates"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return builder.as_markup()

# ==================== ПОДТВЕРЖДЕНИЕ ====================

def confirm_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_booking"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return builder.as_markup()

# ==================== ЗАПРОС ТЕЛЕФОНА ====================

def phone_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📱 Отправить номер", request_contact=True)
    )
    builder.row(
        KeyboardButton(text="❌ Отмена")
    )
    return builder.as_markup(resize_keyboard=True)

# ==================== МОИ ЗАПИСИ ====================

def my_bookings_kb(bookings: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    for booking in bookings:
        builder.row(
            InlineKeyboardButton(
                text=f"❌ Отменить запись #{booking.id}",
                callback_data=f"cancel_booking_{booking.id}"
            )
        )
    
    return builder.as_markup()

# ==================== АДМИН ====================

def admin_booking_kb(booking_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Подтвердить", 
            callback_data=f"admin_confirm_{booking_id}"
        ),
        InlineKeyboardButton(
            text="❌ Отменить", 
            callback_data=f"admin_cancel_{booking_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="✔️ Выполнено", 
            callback_data=f"admin_complete_{booking_id}"
        )
    )
    return builder.as_markup()

def admin_services_kb(services: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    for service in services:
        status = "✅" if service.active else "❌"
        builder.row(
            InlineKeyboardButton(
                text=f"{status} {service.name} — {service.price}₽",
                callback_data=f"admin_service_{service.id}"
            )
        )
    
    return builder.as_markup()

def admin_service_actions_kb(service_id: int, is_active: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    if is_active:
        builder.row(
            InlineKeyboardButton(
                text="🚫 Деактивировать",
                callback_data=f"deactivate_service_{service_id}"
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text="✅ Активировать",
                callback_data=f"activate_service_{service_id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text="🗑 Удалить",
            callback_data=f"delete_service_{service_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_admin_services")
    )
    
    return builder.as_markup()
