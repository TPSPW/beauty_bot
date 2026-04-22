print("Python работает!")
print("Бот будет запущен...")

from aiogram import Bot, Dispatcher
from config import BOT_TOKEN

print(f"Токен загружен: {BOT_TOKEN[:10]}...")

bot = Bot(token=BOT_TOKEN)
print("Бот создан!")
print("Всё ок!")