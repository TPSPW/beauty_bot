import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Токен — вставьте свой прямо сюда для теста
BOT_TOKEN = "8375472372:AAHdn_zFtEoISL04D-gRC789jwA-QME5dMI"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("🟢 Бот работает! Соединение с Telegram установлено.")

@dp.message()
async def echo(message: types.Message):
    await message.answer(f"Вы написали: {message.text}")

async def main():
    print("Запуск бота...")
    print("Бот будет отвечать на сообщения")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())