import sqlite3
from datetime import datetime, timedelta

DB_PATH = "beauty_bot.db"

def get_connection():
    """Создаёт соединение с базой данных"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Создаёт все таблицы в базе данных"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Таблица услуг
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            base_price INTEGER NOT NULL
        )
    ''')
    
    # Таблица городов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cities (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        )
    ''')
    
    # Таблица метро
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS metro_stations (
            id INTEGER PRIMARY KEY,
            city_id INTEGER NOT NULL,
            name TEXT NOT NULL
        )
    ''')
    
    # Таблица салонов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS salons (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            address TEXT NOT NULL,
            metro_id INTEGER NOT NULL,
            city_id INTEGER NOT NULL,
            rating REAL,
            price_level TEXT,
            phone TEXT,
            work_hours TEXT
        )
    ''')
    
    # Таблица услуг салонов (связь и цена)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS salon_services (
            salon_id INTEGER NOT NULL,
            service_id INTEGER NOT NULL,
            price INTEGER NOT NULL,
            PRIMARY KEY (salon_id, service_id)
        )
    ''')
    
    # Таблица временных слотов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS available_slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            salon_id INTEGER NOT NULL,
            booking_date TEXT NOT NULL,
            booking_time TEXT NOT NULL,
            is_available INTEGER DEFAULT 1
        )
    ''')
    
    # Таблица записей клиентов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            service_id INTEGER NOT NULL,
            salon_id INTEGER NOT NULL,
            client_name TEXT NOT NULL,
            client_phone TEXT NOT NULL,
            booking_date TEXT NOT NULL,
            booking_time TEXT NOT NULL,
            price INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")

def load_initial_data():
    """Загружает начальные данные в базу"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Проверяем, есть ли уже данные
    cursor.execute("SELECT COUNT(*) FROM services")
    if cursor.fetchone()[0] > 0:
        print("📦 Данные уже загружены")
        conn.close()
        return
    
    print("📦 Загружаем начальные данные...")
    
    # 1. Услуги
    services = [
        (1, "💅 Маникюр", 1500),
        (2, "💅 Маникюр + покрытие", 2500),
        (3, "🦶 Педикюр", 2000),
        (4, "💇 Женская стрижка", 1800),
        (5, "💇‍♂️ Мужская стрижка", 1200),
        (6, "🎨 Окрашивание", 4000),
        (7, "💆‍♀️ Массаж лица", 2500),
    ]
    cursor.executemany("INSERT INTO services (id, name, base_price) VALUES (?, ?, ?)", services)
    
    # 2. Города
    cities = [
        (1, "Москва"),
        (2, "Санкт-Петербург"),
        (3, "Казань"),
        (4, "Новосибирск"),
    ]
    cursor.executemany("INSERT INTO cities (id, name) VALUES (?, ?)", cities)
    
    # 3. Метро
    metro = [
        (1, 1, "Чертановская"), (2, 1, "Южная"), (3, 1, "Пражская"),
        (4, 1, "Царицыно"), (5, 1, "Аннино"), (6, 1, "Бульвар Дмитрия Донского"),
        (7, 1, "Улица Старокачаловская"), (8, 2, "Невский проспект"),
        (9, 2, "Гостиный двор"), (10, 2, "Маяковская"), (11, 3, "Кремлёвская"),
        (12, 3, "Площадь Тукая"), (13, 4, "Площадь Ленина"), (14, 4, "Речной вокзал"),
    ]
    cursor.executemany("INSERT INTO metro_stations (id, city_id, name) VALUES (?, ?, ?)", metro)
    
    # 4. Салоны
    salons = [
        (1, "💅 Nail Studio Чертаново", "ул. Чертановская, д. 15", 1, 1, 4.9, "средний", "+7 (999) 111-22-33", "10:00 - 21:00"),
        (2, "✂️ Beauty House Южная", "ул. Днепропетровская, д. 12", 2, 1, 4.7, "выше среднего", "+7 (999) 222-33-44", "09:00 - 20:00"),
        (3, "✨ Простория Пражская", "ул. Красного Маяка, д. 8", 3, 1, 4.8, "средний", "+7 (999) 333-44-55", "10:00 - 22:00"),
        (4, "💅 Маникюрный рай Царицыно", "ул. Луганская, д. 5", 4, 1, 4.6, "бюджетный", "+7 (999) 444-55-66", "10:00 - 20:00"),
        (5, "🌟 Салон красоты на Аннино", "ул. Аннино, д. 10", 5, 1, 4.9, "выше среднего", "+7 (999) 555-66-77", "09:00 - 21:00"),
    ]
    cursor.executemany("INSERT INTO salons (id, name, address, metro_id, city_id, rating, price_level, phone, work_hours) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", salons)
    
    # 5. Услуги салонов
    salon_services = [
        (1, 1, 1200), (1, 2, 2200), (1, 3, 1800),
        (2, 4, 2000), (2, 5, 1500), (2, 6, 4500),
        (3, 1, 1500), (3, 2, 2500), (3, 3, 2000), (3, 4, 1800), (3, 5, 1200), (3, 6, 4000), (3, 7, 2500),
        (4, 1, 800), (4, 2, 1500), (4, 3, 1200),
        (5, 1, 1800), (5, 2, 3000), (5, 4, 2200), (5, 7, 2800),
    ]
    cursor.executemany("INSERT INTO salon_services (salon_id, service_id, price) VALUES (?, ?, ?)", salon_services)
    
    # 6. Генерируем слоты на ближайшие 7 дней
    today = datetime.now()
    times = ["10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00"]
    
    for salon_id in range(1, 6):
        for i in range(7):
            date = (today + timedelta(days=i)).strftime("%Y-%m-%d")
            for time_slot in times:
                cursor.execute('''
                    INSERT INTO available_slots (salon_id, booking_date, booking_time, is_available)
                    VALUES (?, ?, ?, 1)
                ''', (salon_id, date, time_slot))
    
    conn.commit()
    conn.close()
    print("✅ Начальные данные загружены")
    # ============ ФУНКЦИИ ДЛЯ РАБОТЫ С БОТОМ ============

def get_all_services():
    """Получить все услуги"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, base_price FROM services")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": row["id"], "name": row["name"], "base_price": row["base_price"]} for row in rows]

def get_all_cities():
    """Получить все города"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM cities")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": row["id"], "name": row["name"]} for row in rows]

def get_metro_by_city(city_id):
    """Получить станции метро по городу"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM metro_stations WHERE city_id = ?", (city_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"id": row["id"], "name": row["name"]} for row in rows]

def get_price_ranges():
    """Ценовые диапазоны (временные данные, можно потом перенести в БД)"""
    return [
        {"id": 1, "name": "💰 до 1000 ₽", "min": 0, "max": 1000},
        {"id": 2, "name": "💰 1000 - 2000 ₽", "min": 1000, "max": 2000},
        {"id": 3, "name": "💰 2000 - 3000 ₽", "min": 2000, "max": 3000},
        {"id": 4, "name": "💰 3000 - 5000 ₽", "min": 3000, "max": 5000},
        {"id": 5, "name": "💰 от 5000 ₽", "min": 5000, "max": 999999},
        {"id": 6, "name": "🎯 Любая цена", "min": 0, "max": 999999},
    ]

def find_salons_by_filters(service_id, price_range_id, city_id, metro_id, date_str, time_str):
    """Найти салоны по всем фильтрам"""
    price_range = next((p for p in get_price_ranges() if p["id"] == price_range_id), get_price_ranges()[-1])
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 
            s.id, s.name, s.address, s.rating, s.price_level, s.phone, s.work_hours,
            ss.price as actual_price
        FROM salons s
        JOIN salon_services ss ON s.id = ss.salon_id
        JOIN available_slots av ON s.id = av.salon_id
        WHERE ss.service_id = ?
            AND s.city_id = ?
            AND s.metro_id = ?
            AND av.booking_date = ?
            AND av.booking_time = ?
            AND av.is_available = 1
    ''', (service_id, city_id, metro_id, date_str, time_str))
    
    rows = cursor.fetchall()
    conn.close()
    
    # Фильтруем по цене
    results = []
    for row in rows:
        if price_range["min"] <= row["actual_price"] <= price_range["max"]:
            results.append(dict(row))
    
    return results

def save_booking(user_id, service_id, salon_id, client_name, client_phone, booking_date, booking_time, price):
    """Сохранить запись в БД и забронировать слот"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Сохраняем запись
    cursor.execute('''
        INSERT INTO bookings (user_id, service_id, salon_id, client_name, client_phone, 
                              booking_date, booking_time, price, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
    ''', (user_id, service_id, salon_id, client_name, client_phone, booking_date, booking_time, price))
    
    booking_id = cursor.lastrowid
    
    # Помечаем слот как занятый
    cursor.execute('''
        UPDATE available_slots SET is_available = 0
        WHERE salon_id = ? AND booking_date = ? AND booking_time = ?
    ''', (salon_id, booking_date, booking_time))
    
    conn.commit()
    conn.close()
    
    return booking_id