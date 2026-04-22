import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ТОКЕН ВАШЕГО БОТА
BOT_TOKEN = "8375472372:AAHdn_zFtEoISL04D-gRC789jwA-QME5dMI"

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ============ СОСТОЯНИЯ ДЛЯ ЗАПИСИ ============
class BookingStates(StatesGroup):
    choosing_service = State()
    choosing_master = State()
    choosing_date = State()
    choosing_time = State()
    entering_name = State()
    entering_phone = State()
    confirming = State()

# ============ ДЕМО-ДАННЫЕ (услуги и мастера) ============
SERVICES = [
    {"id": 1, "name": "💇 Женская стрижка", "price": 1500},
    {"id": 2, "name": "💇‍♂️ Мужская стрижка", "price": 1000},
    {"id": 3, "name": "🎨 Окрашивание", "price": 3500},
    {"id": 4, "name": "💅 Маникюр", "price": 1200},
    {"id": 5, "name": "🦶 Педикюр", "price": 1800},
    {"id": 6, "name": "💆‍♀️ Массаж лица", "price": 2000},
    {"id": 7, "name": "✂️ Детская стрижка", "price": 800},
]

MASTERS = [
    {"id": 1, "name": "👩 Анна (стилист)"},
    {"id": 2, "name": "👨 Дмитрий (барбер)"},
    {"id": 3, "name": "👩 Елена (колорист)"},
    {"id": 4, "name": "👩 Мария (маникюр)"},
]

# Временное хранилище данных пользователя
user_data = {}
# Хранилище ID сообщений текущей сессии (последние 6)
user_messages = {}

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
    """
    Удаляет старые сообщения, оставляя только последние 'keep_last' штук
    keep_last = сколько последних сообщений оставить (чтобы кнопки текущего шага не удалялись)
    """
    if user_id not in user_messages:
        user_messages[user_id] = []
        return
    
    messages = user_messages[user_id]
    # Оставляем последние keep_last сообщений, остальные удаляем
    to_delete = messages[:-keep_last] if len(messages) > keep_last else []
    
    for msg_id in to_delete:
        try:
            await bot.delete_message(chat_id, msg_id)
        except Exception:
            pass
    
    # Обновляем список — оставляем только последние keep_last
    if len(messages) > keep_last:
        user_messages[user_id] = messages[-keep_last:]

async def save_message(user_id, message_id):
    """Сохраняет ID сообщения в историю"""
    if user_id not in user_messages:
        user_messages[user_id] = []
    
    user_messages[user_id].append(message_id)
    
    # Ограничиваем историю 20 сообщениями (на всякий случай)
    if len(user_messages[user_id]) > 20:
        user_messages[user_id] = user_messages[user_id][-20:]

async def clear_session_history(user_id, chat_id):
    """Полностью очищает историю сообщений сессии"""
    if user_id in user_messages:
        for msg_id in user_messages[user_id]:
            try:
                await bot.delete_message(chat_id, msg_id)
            except Exception:
                pass
        user_messages[user_id] = []

# ============ КЛАВИАТУРЫ ============

def get_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Новая запись", callback_data="new_booking")
    builder.button(text="📋 Мои записи", callback_data="my_bookings")
    builder.button(text="ℹ️ О салоне", callback_data="about")
    builder.adjust(1)
    return builder.as_markup()

def get_services_keyboard():
    builder = InlineKeyboardBuilder()
    for service in SERVICES:
        builder.button(
            text=f"{service['name']} — {service['price']} ₽",
            callback_data=f"service_{service['id']}"
        )
    builder.button(text="🔙 В главное меню", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()

def get_masters_keyboard():
    builder = InlineKeyboardBuilder()
    for master in MASTERS:
        builder.button(text=master['name'], callback_data=f"master_{master['id']}")
    builder.button(text="🔙 Назад", callback_data="back_to_services")
    builder.adjust(1)
    return builder.as_markup()

def get_dates_keyboard():
    builder = InlineKeyboardBuilder()
    today = datetime.now()
    for i in range(7):
        date = today + timedelta(days=i)
        date_str = date.strftime("%d.%m.%Y")
        builder.button(text=date_str, callback_data=f"date_{date.strftime('%Y-%m-%d')}")
    builder.button(text="🔙 Назад", callback_data="back_to_masters")
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

def get_confirmation_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="confirm_yes")
    builder.button(text="❌ Отмена", callback_data="confirm_no")
    builder.adjust(2)
    return builder.as_markup()

def get_back_to_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 В главное меню", callback_data="back_to_main")
    return builder.as_markup()

def get_contact_keyboard():
    """Клавиатура с кнопкой для отправки контакта"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Отправить номер телефона", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

# ============ КОМАНДЫ ============

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    # Полная очистка истории
    await clear_session_history(message.from_user.id, message.chat.id)
    await state.clear()
    clear_temp(message.from_user.id)
    
    msg = await message.answer(
        "👋 Добро пожаловать в наш салон красоты!\n\n"
        "✨ Здесь вы можете:\n"
        "• Записаться на процедуру\n"
        "• Посмотреть свои записи\n"
        "• Узнать информацию о салоне\n\n"
        "Выберите действие:",
        reply_markup=get_main_keyboard()
    )
    await save_message(message.from_user.id, msg.message_id)

@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await clear_session_history(message.from_user.id, message.chat.id)
    await state.clear()
    clear_temp(message.from_user.id)
    
    msg = await message.answer(
        "❌ Действие отменено. Возвращаемся в главное меню.",
        reply_markup=get_main_keyboard()
    )
    await save_message(message.from_user.id, msg.message_id)

# ============ НАВИГАЦИЯ ============

@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await clear_session_history(callback.from_user.id, callback.message.chat.id)
    await state.clear()
    clear_temp(callback.from_user.id)
    
    msg = await callback.message.answer(
        "Главное меню:",
        reply_markup=get_main_keyboard()
    )
    await save_message(callback.from_user.id, msg.message_id)
    await callback.answer()

@dp.callback_query(F.data == "back_to_services")
async def back_to_services(callback: types.CallbackQuery, state: FSMContext):
    # Удаляем старые сообщения, оставляем последние 2
    await clean_old_messages(callback.from_user.id, callback.message.chat.id, keep_last=2)
    await state.set_state(BookingStates.choosing_service)
    
    msg = await callback.message.answer(
        "Выберите услугу:",
        reply_markup=get_services_keyboard()
    )
    await save_message(callback.from_user.id, msg.message_id)
    await callback.answer()

@dp.callback_query(F.data == "back_to_masters")
async def back_to_masters(callback: types.CallbackQuery, state: FSMContext):
    await clean_old_messages(callback.from_user.id, callback.message.chat.id, keep_last=2)
    await state.set_state(BookingStates.choosing_master)
    
    msg = await callback.message.answer(
        "Выберите мастера:",
        reply_markup=get_masters_keyboard()
    )
    await save_message(callback.from_user.id, msg.message_id)
    await callback.answer()

@dp.callback_query(F.data == "back_to_dates")
async def back_to_dates(callback: types.CallbackQuery, state: FSMContext):
    await clean_old_messages(callback.from_user.id, callback.message.chat.id, keep_last=2)
    await state.set_state(BookingStates.choosing_date)
    
    msg = await callback.message.answer(
        "Выберите дату:",
        reply_markup=get_dates_keyboard()
    )
    await save_message(callback.from_user.id, msg.message_id)
    await callback.answer()

# ============ О САЛОНЕ ============

@dp.callback_query(F.data == "about")
async def about_salon(callback: types.CallbackQuery):
    await clear_session_history(callback.from_user.id, callback.message.chat.id)
    
    text = (
        "✨ **Наш салон красоты** ✨\n\n"
        "📍 Адрес: ул. Примерная, д. 123\n"
        "🕐 Режим работы: Ежедневно 10:00 - 21:00\n"
        "📞 Телефон: +7 (999) 123-45-67\n\n"
        "💇‍♀️ Мы предлагаем:\n"
        "• Стрижки и укладки\n"
        "• Окрашивание\n"
        "• Маникюр и педикюр\n"
        "• Массаж и уход за лицом\n\n"
        "Ждём вас в нашем салоне! ❤️"
    )
    msg = await callback.message.answer(text, reply_markup=get_back_to_main_keyboard())
    await save_message(callback.from_user.id, msg.message_id)
    await callback.answer()

# ============ МОИ ЗАПИСИ (ДЕМО) ============

@dp.callback_query(F.data == "my_bookings")
async def my_bookings(callback: types.CallbackQuery):
    await clear_session_history(callback.from_user.id, callback.message.chat.id)
    
    text = "📋 Здесь будут ваши записи.\n\nПока что это демо-версия. Полная версия появится после подключения YCLIENTS."
    msg = await callback.message.answer(text, reply_markup=get_back_to_main_keyboard())
    await save_message(callback.from_user.id, msg.message_id)
    await callback.answer()

# ============ НОВАЯ ЗАПИСЬ ============

@dp.callback_query(F.data == "new_booking")
async def new_booking(callback: types.CallbackQuery, state: FSMContext):
    await clear_session_history(callback.from_user.id, callback.message.chat.id)
    await state.set_state(BookingStates.choosing_service)
    
    msg = await callback.message.answer(
        "Выберите услугу:",
        reply_markup=get_services_keyboard()
    )
    await save_message(callback.from_user.id, msg.message_id)
    await callback.answer()

@dp.callback_query(F.data.startswith("service_"))
async def service_chosen(callback: types.CallbackQuery, state: FSMContext):
    service_id = int(callback.data.split("_")[1])
    service = next((s for s in SERVICES if s["id"] == service_id), None)
    
    if service:
        save_temp(callback.from_user.id, "service_id", service_id)
        save_temp(callback.from_user.id, "service_name", service["name"])
        save_temp(callback.from_user.id, "service_price", service["price"])
    
    await clean_old_messages(callback.from_user.id, callback.message.chat.id, keep_last=2)
    await state.set_state(BookingStates.choosing_master)
    
    msg = await callback.message.answer(
        f"💇 Услуга: {service['name']} — {service['price']} ₽\n\nТеперь выберите мастера:",
        reply_markup=get_masters_keyboard()
    )
    await save_message(callback.from_user.id, msg.message_id)
    await callback.answer()

@dp.callback_query(F.data.startswith("master_"))
async def master_chosen(callback: types.CallbackQuery, state: FSMContext):
    master_id = int(callback.data.split("_")[1])
    master = next((m for m in MASTERS if m["id"] == master_id), None)
    
    if master:
        save_temp(callback.from_user.id, "master_id", master_id)
        save_temp(callback.from_user.id, "master_name", master["name"])
    
    await clean_old_messages(callback.from_user.id, callback.message.chat.id, keep_last=2)
    await state.set_state(BookingStates.choosing_date)
    
    msg = await callback.message.answer(
        f"👨‍🎨 Мастер: {master['name']}\n\nВыберите дату:",
        reply_markup=get_dates_keyboard()
    )
    await save_message(callback.from_user.id, msg.message_id)
    await callback.answer()

@dp.callback_query(F.data.startswith("date_"))
async def date_chosen(callback: types.CallbackQuery, state: FSMContext):
    date_str = callback.data.split("_")[1]
    save_temp(callback.from_user.id, "selected_date", date_str)
    
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    formatted_date = date_obj.strftime("%d.%m.%Y")
    save_temp(callback.from_user.id, "formatted_date", formatted_date)
    
    await clean_old_messages(callback.from_user.id, callback.message.chat.id, keep_last=2)
    await state.set_state(BookingStates.choosing_time)
    
    msg = await callback.message.answer(
        f"📅 Дата: {formatted_date}\n\nВыберите удобное время:",
        reply_markup=get_times_keyboard()
    )
    await save_message(callback.from_user.id, msg.message_id)
    await callback.answer()

@dp.callback_query(F.data.startswith("time_"))
async def time_chosen(callback: types.CallbackQuery, state: FSMContext):
    time_str = callback.data.split("_")[1]
    save_temp(callback.from_user.id, "selected_time", time_str)
    
    await clean_old_messages(callback.from_user.id, callback.message.chat.id, keep_last=2)
    await state.set_state(BookingStates.entering_name)
    
    cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Отмена", callback_data="back_to_main")]
    ])
    
    msg = await callback.message.answer(
        f"⏰ Время: {time_str}\n\nВведите ваше имя:",
        reply_markup=cancel_keyboard
    )
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
    # Получаем номер из контакта
    phone = message.contact.phone_number
    save_temp(message.from_user.id, "client_phone", phone)
    
    await clean_old_messages(message.from_user.id, message.chat.id, keep_last=2)
    
    temp = get_temp(message.from_user.id)
    
    confirm_text = (
        "📝 **Проверьте данные записи:**\n\n"
        f"💇 Услуга: {temp.get('service_name', '—')}\n"
        f"💰 Цена: {temp.get('service_price', '—')} ₽\n"
        f"👨‍🎨 Мастер: {temp.get('master_name', '—')}\n"
        f"📅 Дата: {temp.get('formatted_date', '—')}\n"
        f"⏰ Время: {temp.get('selected_time', '—')}\n"
        f"👤 Имя: {temp.get('client_name', '—')}\n"
        f"📞 Телефон: {temp.get('client_phone', '—')}\n\n"
        "Всё верно?"
    )
    
    await state.set_state(BookingStates.confirming)
    msg = await message.answer(
        confirm_text,
        reply_markup=get_confirmation_keyboard()
    )
    await save_message(message.from_user.id, msg.message_id)

# Если пользователь ввел номер вручную (не через кнопку)
@dp.message(BookingStates.entering_phone, F.text)
async def phone_entered_manual(message: types.Message, state: FSMContext):
    await clean_old_messages(message.from_user.id, message.chat.id, keep_last=2)
    
    phone = message.text.strip()
    save_temp(message.from_user.id, "client_phone", phone)
    
    temp = get_temp(message.from_user.id)
    
    confirm_text = (
        "📝 **Проверьте данные записи:**\n\n"
        f"💇 Услуга: {temp.get('service_name', '—')}\n"
        f"💰 Цена: {temp.get('service_price', '—')} ₽\n"
        f"👨‍🎨 Мастер: {temp.get('master_name', '—')}\n"
        f"📅 Дата: {temp.get('formatted_date', '—')}\n"
        f"⏰ Время: {temp.get('selected_time', '—')}\n"
        f"👤 Имя: {temp.get('client_name', '—')}\n"
        f"📞 Телефон: {temp.get('client_phone', '—')}\n\n"
        "Всё верно?"
    )
    
    await state.set_state(BookingStates.confirming)
    msg = await message.answer(
        confirm_text,
        reply_markup=get_confirmation_keyboard()
    )
    await save_message(message.from_user.id, msg.message_id)

@dp.callback_query(F.data == "confirm_yes", StateFilter(BookingStates.confirming))
async def confirm_booking(callback: types.CallbackQuery, state: FSMContext):
    temp = get_temp(callback.from_user.id)
    
    if not temp:
        await clear_session_history(callback.from_user.id, callback.message.chat.id)
        await state.clear()
        msg = await callback.message.answer(
            "Ошибка. Начните запись заново.",
            reply_markup=get_main_keyboard()
        )
        await save_message(callback.from_user.id, msg.message_id)
        await callback.answer()
        return
    
    await clear_session_history(callback.from_user.id, callback.message.chat.id)
    
    success_text = (
        "✅ **Запись успешно создана!**\n\n"
        f"💇 {temp.get('service_name', '—')}\n"
        f"👨‍🎨 {temp.get('master_name', '—')}\n"
        f"📅 {temp.get('formatted_date', '—')} в {temp.get('selected_time', '—')}\n\n"
        "Ждём вас в салоне! ✨\n\n"
        "Напоминание придёт за час до записи."
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
    
    msg = await callback.message.answer(
        "❌ Запись отменена.",
        reply_markup=get_main_keyboard()
    )
    await save_message(callback.from_user.id, msg.message_id)
    await callback.answer()

# ============ ЗАПУСК БОТА ============

async def main():
    print("🤖 Бот запущен!")
    print("Напишите /start в Telegram")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
