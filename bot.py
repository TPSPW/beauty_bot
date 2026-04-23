import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import (
    init_db, load_initial_data,
    get_all_services, get_all_cities, get_metro_by_city,
    get_price_ranges, find_salons_by_filters, save_booking
)

BOT_TOKEN = "8375472372:AAHdn_zFtEoISL04D-gRC789jwA-QME5dMI"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Инициализируем БД
init_db()
load_initial_data()

# ============ СОСТОЯНИЯ ============
class BookingStates(StatesGroup):
    choosing_service = State()
    choosing_price_range = State()
    choosing_city = State()
    choosing_metro = State()
    choosing_date = State()
    choosing_time = State()
    showing_salons = State()
    entering_name = State()
    entering_phone = State()
    confirming = State()

# Временное хранилище
user_data = {}
user_messages = {}

# ============ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ============

def save_temp(user_id, field, value):
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id][field] = value

def get_temp(user_id):
    return user_data.get(user_id, {})

def clear_temp(user_id):
    if user_id in user_data:
        del user_data[user_id]

async def clean_old_messages(user_id, chat_id, keep_last=2):
    if user_id not in user_messages:
        user_messages[user_id] = []
        return
    messages = user_messages[user_id]
    to_delete = messages[:-keep_last] if len(messages) > keep_last else []
    for msg_id in to_delete:
        try:
            await bot.delete_message(chat_id, msg_id)
        except:
            pass
    if len(messages) > keep_last:
        user_messages[user_id] = messages[-keep_last:]

async def save_message(user_id, message_id):
    if user_id not in user_messages:
        user_messages[user_id] = []
    user_messages[user_id].append(message_id)
    if len(user_messages[user_id]) > 20:
        user_messages[user_id] = user_messages[user_id][-20:]

async def clear_session_history(user_id, chat_id):
    if user_id in user_messages:
        for msg_id in user_messages[user_id]:
            try:
                await bot.delete_message(chat_id, msg_id)
            except:
                pass
        user_messages[user_id] = []

# ============ КЛАВИАТУРЫ ============

def get_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Новая запись", callback_data="new_booking")
    builder.button(text="ℹ️ О сервисе", callback_data="about")
    builder.adjust(1)
    return builder.as_markup()

def get_services_keyboard():
    builder = InlineKeyboardBuilder()
    for service in get_all_services():
        builder.button(
            text=f"{service['name']} — от {service['base_price']} ₽",
            callback_data=f"service_{service['id']}"
        )
    builder.button(text="🔙 В главное меню", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()

def get_price_ranges_keyboard():
    builder = InlineKeyboardBuilder()
    for pr in get_price_ranges():
        builder.button(text=pr["name"], callback_data=f"price_{pr['id']}")
    builder.button(text="🔙 Назад", callback_data="back_to_services")
    builder.adjust(1)
    return builder.as_markup()

def get_cities_keyboard():
    builder = InlineKeyboardBuilder()
    for city in get_all_cities():
        builder.button(text=city["name"], callback_data=f"city_{city['id']}")
    builder.button(text="🔙 Назад", callback_data="back_to_price")
    builder.adjust(1)
    return builder.as_markup()

def get_metro_keyboard(city_id):
    builder = InlineKeyboardBuilder()
    for metro in get_metro_by_city(city_id):
        builder.button(text=f"🚇 {metro['name']}", callback_data=f"metro_{metro['id']}")
    builder.button(text="🔙 Назад", callback_data="back_to_cities")
    builder.adjust(1)
    return builder.as_markup()

def get_dates_keyboard():
    builder = InlineKeyboardBuilder()
    today = datetime.now()
    for i in range(7):
        date = today + timedelta(days=i)
        date_str = date.strftime("%d.%m.%Y")
        builder.button(text=date_str, callback_data=f"date_{date.strftime('%Y-%m-%d')}")
    builder.button(text="🔙 Назад", callback_data="back_to_metro")
    builder.adjust(2)
    return builder.as_markup()

def get_times_keyboard():
    builder = InlineKeyboardBuilder()
    times = ["10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00"]
    for t in times:
        builder.button(text=t, callback_data=f"time_{t}")
    builder.button(text="🔙 Назад", callback_data="back_to_dates")
    builder.adjust(3)
    return builder.as_markup()

def get_salons_keyboard(salons):
    builder = InlineKeyboardBuilder()
    for salon in salons:
        builder.button(
            text=f"{salon['name']} ⭐ {salon['rating']} — {salon['actual_price']} ₽",
            callback_data=f"salon_{salon['id']}"
        )
    builder.button(text="🔄 Начать заново", callback_data="new_booking")
    builder.adjust(1)
    return builder.as_markup()

def get_salon_details_keyboard(salon_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Записаться в этот салон", callback_data=f"book_salon_{salon_id}")
    builder.button(text="🔍 Поиск других салонов", callback_data="new_booking")
    builder.button(text="🔙 В главное меню", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()

def get_confirmation_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="confirm_yes")
    builder.button(text="❌ Отмена", callback_data="confirm_no")
    builder.adjust(2)
    return builder.as_markup()

def get_contact_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Отправить номер телефона", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

def get_back_to_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 В главное меню", callback_data="back_to_main")
    return builder.as_markup()

# ============ КОМАНДЫ ============

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await clear_session_history(message.from_user.id, message.chat.id)
    await state.clear()
    clear_temp(message.from_user.id)
    msg = await message.answer(
        "👋 Добро пожаловать в сервис поиска салонов красоты!\n\n"
        "✨ Вы сможете:\n"
        "• Выбрать услугу\n"
        "• Указать бюджет\n"
        "• Выбрать город и метро\n"
        "• Выбрать удобную дату и время\n"
        "• Найти ближайшие салоны\n\n"
        "Начнём? 👇",
        reply_markup=get_main_keyboard()
    )
    await save_message(message.from_user.id, msg.message_id)

# ============ НАВИГАЦИЯ ============

@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await clear_session_history(callback.from_user.id, callback.message.chat.id)
    await state.clear()
    clear_temp(callback.from_user.id)
    msg = await callback.message.answer("Главное меню:", reply_markup=get_main_keyboard())
    await save_message(callback.from_user.id, msg.message_id)
    await callback.answer()

@dp.callback_query(F.data == "back_to_services")
async def back_to_services(callback: types.CallbackQuery, state: FSMContext):
    await clean_old_messages(callback.from_user.id, callback.message.chat.id, keep_last=2)
    await state.set_state(BookingStates.choosing_service)
    msg = await callback.message.answer("Выберите услугу:", reply_markup=get_services_keyboard())
    await save_message(callback.from_user.id, msg.message_id)
    await callback.answer()

@dp.callback_query(F.data == "back_to_price")
async def back_to_price(callback: types.CallbackQuery, state: FSMContext):
    await clean_old_messages(callback.from_user.id, callback.message.chat.id, keep_last=2)
    await state.set_state(BookingStates.choosing_price_range)
    msg = await callback.message.answer("Выберите ценовой диапазон:", reply_markup=get_price_ranges_keyboard())
    await save_message(callback.from_user.id, msg.message_id)
    await callback.answer()

@dp.callback_query(F.data == "back_to_cities")
async def back_to_cities(callback: types.CallbackQuery, state: FSMContext):
    await clean_old_messages(callback.from_user.id, callback.message.chat.id, keep_last=2)
    await state.set_state(BookingStates.choosing_city)
    msg = await callback.message.answer("Выберите город:", reply_markup=get_cities_keyboard())
    await save_message(callback.from_user.id, msg.message_id)
    await callback.answer()

@dp.callback_query(F.data == "back_to_metro")
async def back_to_metro(callback: types.CallbackQuery, state: FSMContext):
    temp = get_temp(callback.from_user.id)
    city_id = temp.get("city_id")
    await clean_old_messages(callback.from_user.id, callback.message.chat.id, keep_last=2)
    await state.set_state(BookingStates.choosing_metro)
    msg = await callback.message.answer("Выберите станцию метро:", reply_markup=get_metro_keyboard(city_id))
    await save_message(callback.from_user.id, msg.message_id)
    await callback.answer()

@dp.callback_query(F.data == "back_to_dates")
async def back_to_dates(callback: types.CallbackQuery, state: FSMContext):
    await clean_old_messages(callback.from_user.id, callback.message.chat.id, keep_last=2)
    await state.set_state(BookingStates.choosing_date)
    msg = await callback.message.answer("Выберите дату:", reply_markup=get_dates_keyboard())
    await save_message(callback.from_user.id, msg.message_id)
    await callback.answer()

# ============ ОСНОВНОЙ ПОТОК ============

@dp.callback_query(F.data == "new_booking")
async def new_booking(callback: types.CallbackQuery, state: FSMContext):
    await clear_session_history(callback.from_user.id, callback.message.chat.id)
    await state.set_state(BookingStates.choosing_service)
    msg = await callback.message.answer("🎯 Шаг 1 из 6: Выберите услугу", reply_markup=get_services_keyboard())
    await save_message(callback.from_user.id, msg.message_id)
    await callback.answer()

@dp.callback_query(F.data.startswith("service_"))
async def service_chosen(callback: types.CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split("_")[1])
    services = get_all_services()
    service = next((s for s in services if s["id"] == service_id), None)
    if service:
        save_temp(callback.from_user.id, "service_id", service_id)
        save_temp(callback.from_user.id, "service_name", service["name"])
    
    await clean_old_messages(callback.from_user.id, callback.message.chat.id, keep_last=2)
    await state.set_state(BookingStates.choosing_price_range)
    msg = await callback.message.answer(
        f"✅ Услуга: {service['name']}\n\n💰 Шаг 2 из 6: Выберите ценовой диапазон",
        reply_markup=get_price_ranges_keyboard()
    )
    await save_message(callback.from_user.id, msg.message_id)
    await callback.answer()

@dp.callback_query(F.data.startswith("price_"))
async def price_range_chosen(callback: types.CallbackQuery, state: FSMContext):
    price_range_id = int(callback.data.split("_")[1])
    price_ranges = get_price_ranges()
    price_range = next((p for p in price_ranges if p["id"] == price_range_id), price_ranges[-1])
    save_temp(callback.from_user.id, "price_range_id", price_range_id)
    save_temp(callback.from_user.id, "price_range_name", price_range["name"])
    
    await clean_old_messages(callback.from_user.id, callback.message.chat.id, keep_last=2)
    await state.set_state(BookingStates.choosing_city)
    msg = await callback.message.answer(
        f"✅ Бюджет: {price_range['name']}\n\n🌍 Шаг 3 из 6: Выберите город",
        reply_markup=get_cities_keyboard()
    )
    await save_message(callback.from_user.id, msg.message_id)
    await callback.answer()

@dp.callback_query(F.data.startswith("city_"))
async def city_chosen(callback: types.CallbackQuery, state: FSMContext):
    city_id = int(callback.data.split("_")[1])
    cities = get_all_cities()
    city = next((c for c in cities if c["id"] == city_id), None)
    if city:
        save_temp(callback.from_user.id, "city_id", city_id)
        save_temp(callback.from_user.id, "city_name", city["name"])
    
    await clean_old_messages(callback.from_user.id, callback.message.chat.id, keep_last=2)
    await state.set_state(BookingStates.choosing_metro)
    msg = await callback.message.answer(
        f"✅ Город: {city['name']}\n\n🚇 Шаг 4 из 6: Выберите станцию метро",
        reply_markup=get_metro_keyboard(city_id)
    )
    await save_message(callback.from_user.id, msg.message_id)
    await callback.answer()

@dp.callback_query(F.data.startswith("metro_"))
async def metro_chosen(callback: types.CallbackQuery, state: FSMContext):
    metro_id = int(callback.data.split("_")[1])
    temp = get_temp(callback.from_user.id)
    city_id = temp.get("city_id")
    metros = get_metro_by_city(city_id)
    metro_name = next((m["name"] for m in metros if m["id"] == metro_id), "Неизвестно")
    save_temp(callback.from_user.id, "metro_id", metro_id)
    save_temp(callback.from_user.id, "metro_name", metro_name)
    
    await clean_old_messages(callback.from_user.id, callback.message.chat.id, keep_last=2)
    await state.set_state(BookingStates.choosing_date)
    msg = await callback.message.answer(
        f"✅ Станция метро: {metro_name}\n\n📅 Шаг 5 из 6: Выберите дату",
        reply_markup=get_dates_keyboard()
    )
    await save_message(callback.from_user.id, msg.message_id)
    await callback.answer()

@dp.callback_query(F.data.startswith("date_"))
async def date_chosen(callback: types.CallbackQuery, state: FSMContext):
    date_str = callback.data.split("_")[1]
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    formatted_date = date_obj.strftime("%d.%m.%Y")
    save_temp(callback.from_user.id, "selected_date", date_str)
    save_temp(callback.from_user.id, "formatted_date", formatted_date)
    
    await clean_old_messages(callback.from_user.id, callback.message.chat.id, keep_last=2)
    await state.set_state(BookingStates.choosing_time)
    msg = await callback.message.answer(
        f"✅ Дата: {formatted_date}\n\n⏰ Шаг 6 из 6: Выберите время",
        reply_markup=get_times_keyboard()
    )
    await save_message(callback.from_user.id, msg.message_id)
    await callback.answer()

@dp.callback_query(F.data.startswith("time_"))
async def time_chosen(callback: types.CallbackQuery, state: FSMContext):
    time_str = callback.data.split("_")[1]
    save_temp(callback.from_user.id, "selected_time", time_str)
    
    temp = get_temp(callback.from_user.id)
    
    salons = find_salons_by_filters(
        temp.get("service_id"),
        temp.get("price_range_id"),
        temp.get("city_id"),
        temp.get("metro_id"),
        temp.get("selected_date"),
        time_str
    )
    
    save_temp(callback.from_user.id, "found_salons", salons)
    
    await clean_old_messages(callback.from_user.id, callback.message.chat.id, keep_last=2)
    
    if not salons:
        msg = await callback.message.answer(
            "😔 К сожалению, по вашим критериям не найдено салонов.\n\nПопробуйте изменить параметры поиска:",
            reply_markup=get_back_to_main_keyboard()
        )
        await save_message(callback.from_user.id, msg.message_id)
        await callback.answer()
        return
    
    salons_text = f"🔍 Найдено {len(salons)} салонов:\n\n"
    for s in salons:
        salons_text += f"🏢 {s['name']}\n📍 {s['address']}\n⭐ {s['rating']}\n💰 {s['actual_price']} ₽\n\n"
    
    msg = await callback.message.answer(
        f"✅ Время: {time_str}\n\n{salons_text}Выберите салон для записи:",
        reply_markup=get_salons_keyboard(salons)
    )
    await save_message(callback.from_user.id, msg.message_id)
    await callback.answer()

@dp.callback_query(F.data.startswith("salon_"))
async def salon_chosen(callback: types.CallbackQuery, state: FSMContext):
    salon_id = int(callback.data.split("_")[1])
    temp = get_temp(callback.from_user.id)
    salons = temp.get("found_salons", [])
    salon = next((s for s in salons if s["id"] == salon_id), None)
    
    if salon:
        save_temp(callback.from_user.id, "selected_salon_id", salon_id)
        save_temp(callback.from_user.id, "selected_salon_name", salon["name"])
        save_temp(callback.from_user.id, "selected_salon_address", salon["address"])
        save_temp(callback.from_user.id, "selected_salon_phone", salon["phone"])
        save_temp(callback.from_user.id, "actual_price", salon["actual_price"])
    
    await clean_old_messages(callback.from_user.id, callback.message.chat.id, keep_last=2)
    
    details_text = (
        f"🏢 **{salon['name']}**\n\n"
        f"📍 Адрес: {salon['address']}\n"
        f"📞 Телефон: {salon['phone']}\n"
        f"⭐ Рейтинг: {salon['rating']}\n"
        f"💰 Цена: {salon['actual_price']} ₽\n"
        f"💇 Услуга: {temp.get('service_name')}\n"
        f"📅 Дата: {temp.get('formatted_date')}\n"
        f"⏰ Время: {temp.get('selected_time')}\n\n"
        f"Хотите записаться в этот салон?"
    )
    
    msg = await callback.message.answer(details_text, reply_markup=get_salon_details_keyboard(salon_id))
    await save_message(callback.from_user.id, msg.message_id)
    await callback.answer()

@dp.callback_query(F.data.startswith("book_salon_"))
async def book_salon(callback: types.CallbackQuery, state: FSMContext):
    await clean_old_messages(callback.from_user.id, callback.message.chat.id, keep_last=2)
    await state.set_state(BookingStates.entering_name)
    cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Отмена", callback_data="back_to_main")]
    ])
    msg = await callback.message.answer("✏️ Введите ваше имя:", reply_markup=cancel_keyboard)
    await save_message(callback.from_user.id, msg.message_id)
    await callback.answer()

@dp.message(BookingStates.entering_name)
async def name_entered(message: types.Message, state: FSMContext):
    await clean_old_messages(message.from_user.id, message.chat.id, keep_last=2)
    if len(message.text.strip()) < 2:
        msg = await message.answer("Пожалуйста, введите корректное имя (минимум 2 символа):")
        await save_message(message.from_user.id, msg.message_id)
        return
    save_temp(message.from_user.id, "client_name", message.text.strip())
    await state.set_state(BookingStates.entering_phone)
    msg = await message.answer(
        f"👤 Имя: {message.text.strip()}\n\nПоделитесь вашим номером телефона:",
        reply_markup=get_contact_keyboard()
    )
    await save_message(message.from_user.id, msg.message_id)

@dp.message(BookingStates.entering_phone, F.contact)
async def contact_received(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number
    save_temp(message.from_user.id, "client_phone", phone)
    await clean_old_messages(message.from_user.id, message.chat.id, keep_last=2)
    temp = get_temp(message.from_user.id)
    confirm_text = (
        "📝 **Проверьте данные записи:**\n\n"
        f"💇 Услуга: {temp.get('service_name', '—')}\n"
        f"💰 Цена: {temp.get('actual_price', '—')} ₽\n"
        f"🏢 Салон: {temp.get('selected_salon_name', '—')}\n"
        f"📍 Адрес: {temp.get('selected_salon_address', '—')}\n"
        f"📅 Дата: {temp.get('formatted_date', '—')}\n"
        f"⏰ Время: {temp.get('selected_time', '—')}\n"
        f"👤 Имя: {temp.get('client_name', '—')}\n"
        f"📞 Телефон: {temp.get('client_phone', '—')}\n\n"
        "Всё верно?"
    )
    await state.set_state(BookingStates.confirming)
    msg = await message.answer(confirm_text, reply_markup=get_confirmation_keyboard())
    await save_message(message.from_user.id, msg.message_id)

@dp.message(BookingStates.entering_phone, F.text)
async def phone_entered_manual(message: types.Message, state: FSMContext):
    await clean_old_messages(message.from_user.id, message.chat.id, keep_last=2)
    phone = message.text.strip()
    save_temp(message.from_user.id, "client_phone", phone)
    temp = get_temp(message.from_user.id)
    confirm_text = (
        "📝 **Проверьте данные записи:**\n\n"
        f"💇 Услуга: {temp.get('service_name', '—')}\n"
        f"💰 Цена: {temp.get('actual_price', '—')} ₽\n"
        f"🏢 Салон: {temp.get('selected_salon_name', '—')}\n"
        f"📍 Адрес: {temp.get('selected_salon_address', '—')}\n"
        f"📅 Дата: {temp.get('formatted_date', '—')}\n"
        f"⏰ Время: {temp.get('selected_time', '—')}\n"
        f"👤 Имя: {temp.get('client_name', '—')}\n"
        f"📞 Телефон: {temp.get('client_phone', '—')}\n\n"
        "Всё верно?"
    )
    await state.set_state(BookingStates.confirming)
    msg = await message.answer(confirm_text, reply_markup=get_confirmation_keyboard())
    await save_message(message.from_user.id, msg.message_id)

@dp.callback_query(F.data == "confirm_yes", StateFilter(BookingStates.confirming))
async def confirm_booking(callback: types.CallbackQuery, state: FSMContext):
    temp = get_temp(callback.from_user.id)
    if not temp:
        await clear_session_history(callback.from_user.id, callback.message.chat.id)
        await state.clear()
        msg = await callback.message.answer("Ошибка. Начните заново.", reply_markup=get_main_keyboard())
        await save_message(callback.from_user.id, msg.message_id)
        await callback.answer()
        return
    
    save_booking(
        user_id=callback.from_user.id,
        service_id=temp.get("service_id"),
        salon_id=temp.get("selected_salon_id"),
        client_name=temp.get("client_name"),
        client_phone=temp.get("client_phone"),
        booking_date=temp.get("selected_date"),
        booking_time=temp.get("selected_time"),
        price=temp.get("actual_price")
    )
    
    await clear_session_history(callback.from_user.id, callback.message.chat.id)
    
    success_text = (
        "✅ **Запись успешно создана!**\n\n"
        f"💇 {temp.get('service_name', '—')}\n"
        f"💰 {temp.get('actual_price', '—')} ₽\n"
        f"🏢 {temp.get('selected_salon_name', '—')}\n"
        f"📍 {temp.get('selected_salon_address', '—')}\n"
        f"📅 {temp.get('formatted_date', '—')} в {temp.get('selected_time', '—')}\n"
        f"👤 Клиент: {temp.get('client_name', '—')}\n"
        f"📞 Телефон: {temp.get('client_phone', '—')}\n\n"
        "Салон свяжется с вами для подтверждения.\n"
        "Ждём вас! ✨"
    )
    msg = await callback.message.answer(success_text, reply_markup=get_main_keyboard())
    await save_message(callback.from_user.id, msg.message_id)
    clear_temp(callback.from_user.id)
    await state.clear()
    await callback.answer()

@dp.callback_query(F.data == "confirm_no", StateFilter(BookingStates.confirming))
async def cancel_booking(callback: types.CallbackQuery, state: FSMContext):
    await clear_session_history(callback.from_user.id, callback.message.chat.id)
    clear_temp(callback.from_user.id)
    await state.clear()
    msg = await callback.message.answer("❌ Запись отменена.", reply_markup=get_main_keyboard())
    await save_message(callback.from_user.id, msg.message_id)
    await callback.answer()

@dp.callback_query(F.data == "about")
async def about_service(callback: types.CallbackQuery):
    await clear_session_history(callback.from_user.id, callback.message.chat.id)
    text = (
        "✨ **О сервисе** ✨\n\n"
        "Этот бот помогает записаться в салон красоты.\n\n"
        "Выбирайте услугу, бюджет, город, метро,\n"
        "дату и время — бот покажет подходящие салоны!"
    )
    msg = await callback.message.answer(text, reply_markup=get_back_to_main_keyboard())
    await save_message(callback.from_user.id, msg.message_id)
    await callback.answer()

# ============ ЗАПУСК ============

async def main():
    print("🤖 Бот запущен!")
    print("Напишите /start в Telegram")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
