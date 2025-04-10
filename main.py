from aiogram import Bot, Dispatcher, executor, types

# Указываем токен бота
BOT_TOKEN = '8158783896:AAHJgdIfvl1GT9JnM7Wbwa2wOQKQUc2ad1o'

# Инициализируем бота и диспетчер
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Обработчик команды /start
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.answer("Привет!")

# Запуск бота
if __name__ == '__main__':
    print("Бот запущен...")
    executor.start_polling(dp, skip_updates=True)
