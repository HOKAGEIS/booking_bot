import aiosqlite
from datetime import datetime, date
from typing import Optional, List
from dataclasses import dataclass

DATABASE = "booking.db"

@dataclass
class Service:
    id: int
    name: str
    price: int
    duration: int  # минут
    active: bool = True

@dataclass
class Master:
    id: int
    name: str
    services: str  # JSON список ID услуг
    active: bool = True

@dataclass
class Booking:
    id: int
    user_id: int
    user_name: str
    user_phone: str
    service_id: int
    master_id: Optional[int]
    date: str
    time: str
    status: str  # pending, confirmed, cancelled, completed
    created_at: str

async def init_db():
    """Инициализация базы данных"""
    async with aiosqlite.connect(DATABASE) as db:
        # Таблица услуг
        await db.execute("""
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price INTEGER NOT NULL,
                duration INTEGER DEFAULT 60,
                active BOOLEAN DEFAULT 1
            )
        """)
        
        # Таблица мастеров
        await db.execute("""
            CREATE TABLE IF NOT EXISTS masters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                services TEXT DEFAULT '[]',
                active BOOLEAN DEFAULT 1
            )
        """)
        
        # Таблица записей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                user_name TEXT,
                user_phone TEXT,
                service_id INTEGER,
                master_id INTEGER,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (service_id) REFERENCES services(id),
                FOREIGN KEY (master_id) REFERENCES masters(id)
            )
        """)
        
        # Таблица пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                phone TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await db.commit()
        
        # Добавляем демо-данные если пусто
        cursor = await db.execute("SELECT COUNT(*) FROM services")
        count = await cursor.fetchone()
        if count[0] == 0:
            await add_demo_data(db)

async def add_demo_data(db):
    """Добавление демо-данных"""
    services = [
        ("Мужская стрижка", 800, 45),
        ("Женская стрижка", 1500, 60),
        ("Окрашивание", 3000, 120),
        ("Укладка", 1000, 30),
        ("Маникюр", 1200, 60),
    ]
    await db.executemany(
        "INSERT INTO services (name, price, duration) VALUES (?, ?, ?)",
        services
    )
    
    masters = [
        ("Анна", "[1,2,3,4]"),
        ("Мария", "[1,2,4,5]"),
        ("Иван", "[1]"),
    ]
    await db.executemany(
        "INSERT INTO masters (name, services) VALUES (?, ?)",
        masters
    )
    await db.commit()

# ==================== УСЛУГИ ====================

async def get_services(active_only: bool = True) -> List[Service]:
    async with aiosqlite.connect(DATABASE) as db:
        if active_only:
            cursor = await db.execute(
                "SELECT * FROM services WHERE active = 1"
            )
        else:
            cursor = await db.execute("SELECT * FROM services")
        rows = await cursor.fetchall()
        return [Service(*row) for row in rows]

async def get_service(service_id: int) -> Optional[Service]:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            "SELECT * FROM services WHERE id = ?", (service_id,)
        )
        row = await cursor.fetchone()
        return Service(*row) if row else None

async def add_service(name: str, price: int, duration: int = 60) -> int:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            "INSERT INTO services (name, price, duration) VALUES (?, ?, ?)",
            (name, price, duration)
        )
        await db.commit()
        return cursor.lastrowid

async def delete_service(service_id: int):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            "UPDATE services SET active = 0 WHERE id = ?", (service_id,)
        )
        await db.commit()

# ==================== МАСТЕРА ====================

async def get_masters(active_only: bool = True) -> List[Master]:
    async with aiosqlite.connect(DATABASE) as db:
        if active_only:
            cursor = await db.execute(
                "SELECT * FROM masters WHERE active = 1"
            )
        else:
            cursor = await db.execute("SELECT * FROM masters")
        rows = await cursor.fetchall()
        return [Master(*row) for row in rows]

async def get_master(master_id: int) -> Optional[Master]:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            "SELECT * FROM masters WHERE id = ?", (master_id,)
        )
        row = await cursor.fetchone()
        return Master(*row) if row else None

async def get_masters_for_service(service_id: int) -> List[Master]:
    """Получить мастеров, которые делают эту услугу"""
    masters = await get_masters()
    import json
    result = []
    for master in masters:
        services = json.loads(master.services)
        if service_id in services:
            result.append(master)
    return result

# ==================== ЗАПИСИ ====================

async def get_booked_slots(date_str: str, master_id: int = None) -> List[str]:
    """Получить занятые слоты на дату"""
    async with aiosqlite.connect(DATABASE) as db:
        if master_id:
            cursor = await db.execute(
                """SELECT time FROM bookings 
                   WHERE date = ? AND master_id = ? AND status != 'cancelled'""",
                (date_str, master_id)
            )
        else:
            cursor = await db.execute(
                """SELECT time FROM bookings 
                   WHERE date = ? AND status != 'cancelled'""",
                (date_str,)
            )
        rows = await cursor.fetchall()
        return [row[0] for row in rows]

async def create_booking(
    user_id: int,
    user_name: str,
    user_phone: str,
    service_id: int,
    master_id: int,
    date_str: str,
    time_str: str
) -> int:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            """INSERT INTO bookings 
               (user_id, user_name, user_phone, service_id, master_id, date, time)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, user_name, user_phone, service_id, master_id, date_str, time_str)
        )
        await db.commit()
        return cursor.lastrowid

async def get_user_bookings(user_id: int) -> List[Booking]:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            """SELECT * FROM bookings 
               WHERE user_id = ? AND status != 'cancelled'
               ORDER BY date, time""",
            (user_id,)
        )
        rows = await cursor.fetchall()
        return [Booking(*row) for row in rows]

async def get_all_bookings(status: str = None) -> List[Booking]:
    async with aiosqlite.connect(DATABASE) as db:
        if status:
            cursor = await db.execute(
                "SELECT * FROM bookings WHERE status = ? ORDER BY date, time",
                (status,)
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM bookings ORDER BY date DESC, time"
            )
        rows = await cursor.fetchall()
        return [Booking(*row) for row in rows]

async def get_booking(booking_id: int) -> Optional[Booking]:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            "SELECT * FROM bookings WHERE id = ?", (booking_id,)
        )
        row = await cursor.fetchone()
        return Booking(*row) if row else None

async def update_booking_status(booking_id: int, status: str):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            "UPDATE bookings SET status = ? WHERE id = ?",
            (status, booking_id)
        )
        await db.commit()

async def cancel_booking(booking_id: int):
    await update_booking_status(booking_id, "cancelled")

# ==================== ПОЛЬЗОВАТЕЛИ ====================

async def save_user(user_id: int, username: str, full_name: str, phone: str = None):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            """INSERT OR REPLACE INTO users (id, username, full_name, phone)
               VALUES (?, ?, ?, ?)""",
            (user_id, username, full_name, phone)
        )
        await db.commit()

async def get_user_phone(user_id: int) -> Optional[str]:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            "SELECT phone FROM users WHERE id = ?", (user_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else None

async def update_user_phone(user_id: int, phone: str):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            "UPDATE users SET phone = ? WHERE id = ?", (phone, user_id)
        )
        await db.commit()
