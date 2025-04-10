import os
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота
API_TOKEN = '8158783896:AAHJgdIfvl1GT9JnM7Wbwa2wOQKQUc2ad1o'
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Клавиатура выбора препарата
drugs_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Эптифибатид"), KeyboardButton(text="Агграстат")],
    ],
    resize_keyboard=True
)

# Состояния FSM
class Form(StatesGroup):
    drug_choice = State()
    weight = State()
    renal_function = State()

# Установка команд меню (для aiogram 2.x)
async def set_bot_commands():
    commands = [
        types.BotCommand(command="/start", description="Главное меню"),
        types.BotCommand(command="/calculate", description="Расчет дозы"),
        types.BotCommand(command="/protocol", description="Инструкции")
    ]
    await bot.set_my_commands(commands)

# Обработчик /start и /help
@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    await message.reply(
        "🏥 Бот расчета доз антитромбоцитарных препаратов\n\n"
        "Доступные команды:\n"
        "/calculate - начать расчет\n"
        "/protocol - официальные рекомендации\n\n"
        "⚠️ Для медицинских работников! Требуется проверка врача!",
        reply_markup=types.ReplyKeyboardRemove()
    )

# Обработчик /protocol
@dp.message_handler(commands=['protocol'])
async def show_protocol(message: types.Message):
    protocol_text = (
        "📚 Официальные рекомендации:\n\n"
        "💊 Эптифибатид (Интегрилин):\n"
        "▫️ Болюс: 180 мкг/кг (макс 22.6 мг)\n"
        "▫️ Инфузия: 2 мкг/кг/мин (1 мкг/кг/мин при Cl <50)\n\n"
        "💊 Агграстат (Тирофибан):\n"
        "▫️ Болюс: 25 мкг/кг\n"
        "▫️ Инфузия: 0.15 мкг/кг/мин (при Cl <30 - 0.075 мкг/кг/мин)\n\n"
        "⚠️ Максимальные дозы:\n"
        "- Эптифибатид: инфузия 15 мг/час\n"
        "- Агграстат: инфузия 40 мг/час"
    )
    await message.reply(protocol_text)

# Обработчик /calculate
@dp.message_handler(commands=['calculate'])
async def calculate_start(message: types.Message):
    await Form.drug_choice.set()
    await message.reply("Выберите препарат:", reply_markup=drugs_keyboard)

# Обработчик выбора препарата
@dp.message_handler(state=Form.drug_choice)
async def process_drug_choice(message: types.Message, state: FSMContext):
    if message.text not in ["Эптифибатид", "Агграстат"]:
        await message.reply("❌ Пожалуйста, выберите препарат используя кнопки ниже")
        return
    
    async with state.proxy() as data:
        data['drug'] = message.text
    
    await Form.weight.set()
    await message.reply("Введите вес пациента (кг):", reply_markup=types.ReplyKeyboardRemove())

# Обработчик веса
@dp.message_handler(state=Form.weight)
async def process_weight(message: types.Message, state: FSMContext):
    try:
        weight = float(message.text.replace(',', '.'))
        if weight <= 0:
            raise ValueError
            
        async with state.proxy() as data:
            data['weight'] = weight
            
        await Form.renal_function.set()
        await message.reply("Введите клиренс креатинина (мл/мин):")
        
    except ValueError:
        await message.reply("❌ Ошибка! Введите положительное число (например: 75)")
        return

# Обработчик клиренса
@dp.message_handler(state=Form.renal_function)
async def process_renal(message: types.Message, state: FSMContext):
    try:
        cl = float(message.text.replace(',', '.'))
        if cl <= 0:
            raise ValueError
            
        async with state.proxy() as data:
            drug = data['drug']
            weight = data['weight']
            
        if drug == "Эптифибатид":
            # Расчет для Эптифибатида
            bolus = min(weight * 180 / 1000, 22.6)
            infusion_rate = 1 if cl < 50 else 2
            infusion = min(weight * infusion_rate * 60 / 1000, 15)
            note = " (коррекция при почечной недостаточности)" if cl < 50 else ""
            
        elif drug == "Агграстат":
            # Расчет для Агграстата
            bolus = weight * 25 / 1000
            infusion_rate = 0.075 if cl < 30 else 0.15
            infusion = weight * infusion_rate * 60
            note = " (коррекция при почечной недостаточности)" if cl < 30 else ""
        
        response = (
            f"📋 Результаты для {drug}:\n"
            f"▪️ Вес: {weight} кг\n"
            f"▪️ Клиренс креатинина: {cl} мл/мин\n\n"
            f"💉 Болюсная доза: {bolus:.2f} мг\n"
            f"🔄 Инфузия: {infusion:.2f} мг/час{note}\n\n"
            "⚠️ Обязателен контроль врача перед применением!"
        )
        
        await message.reply(response)
        await state.finish()
        
    except ValueError:
        await message.reply("❌ Ошибка! Введите числовое значение (например: 65)")
        return

if __name__ == '__main__':
    # Установка команд меню при старте
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True, on_startup=set_bot_commands)
