import os
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import BotCommand, ReplyKeyboardMarkup, KeyboardButton

# Конфигурация бота
API_TOKEN = os.getenv('TELEGRAM_API_TOKEN')

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Регистрация команд меню
async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="/start", description="Перезапустить"),
        BotCommand(command="/help", description="Помощь"),
        BotCommand(command="/calculate", description="Расчет дозы"),
        BotCommand(command="/protocol", description="Инструкции")
    ]
    await bot.set_my_commands(commands)

# Состояния FSM
class Form(StatesGroup):
    drug_choice = State()
    weight = State()
    renal_function = State()

# Клавиатура выбора препарата
drugs_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Эптифибатид"), KeyboardButton(text="Агграстат")],
    ],
    resize_keyboard=True
)

# Обработчик команд /start и /help
@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    await message.reply(
        "🏥 Бот расчета доз антитромбоцитарных препаратов\n\n"
        "Доступные команды:\n"
        "/calculate - начать расчет\n"
        "/protocol - официальные рекомендации\n\n"
        "⚠️ Для медицинских работников! Требуется проверка врача!"
    )

# Обработчик команды /protocol
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

# Обработчик команды /calculate
@dp.message_handler(commands=['calculate'], state='*')
async def calculate_start(message: types.Message):
    await Form.drug_choice.set()
    await message.reply("Выберите препарат:", reply_markup=drugs_keyboard)

# Обработчик выбора препарата
@dp.message_handler(state=Form.drug_choice)
async def process_drug_choice(message: types.Message, state: FSMContext):
    if message.text not in ["Эптифибатид", "Агграстат"]:
        await message.reply("❌ Неверный выбор! Используйте кнопки ниже")
        return
    
    async with state.proxy() as data:
        data['drug'] = message.text
    
    await Form.weight.set()
    await message.reply("Введите вес пациента (кг):", reply_markup=types.ReplyKeyboardRemove())

# Обработчик ввода веса
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

# Обработчик ввода клиренса
@dp.message_handler(state=Form.renal_function)
async def process_renal(message: types.Message, state: FSMContext):
    try:
        cl = float(message.text.replace(',', '.'))
        if cl <= 0:
            raise ValueError
            
        async with state.proxy() as data:
            drug = data['drug']
            weight = data['weight']
            
        # Расчет для Эптифибатида
        if drug == "Эптифибатид":
            bolus = min(weight * 180 / 1000, 22.6)
            infusion_rate = 1 if cl < 50 else 2
            infusion = min(weight * infusion_rate * 60 / 1000, 15)
            
        # Расчет для Агграстата
        elif drug == "Агграстат":
            bolus = weight * 25 / 1000
            infusion_rate = 0.075 if cl < 30 else 0.15
            infusion = weight * infusion_rate * 60
            
        response = (
            f"📋 Результаты для {drug} ({weight} кг, Cl {cl} мл/мин):\n\n"
            f"💉 Болюсная доза: {bolus:.2f} мг\n"
            f"🔄 Инфузия: {infusion:.2f} мг/час\n\n"
            f"{'🚩 Коррекция дозы при почечной недостаточности' if (cl <50 and drug=='Эптифибатид') or (cl <30 and drug=='Агграстат') else ''}\n"
            "⚠️ Обязателен контроль врача!"
        )
        
        await message.reply(response)
        await state.finish()
        
    except ValueError:
        await message.reply("❌ Ошибка! Введите числовое значение (например: 65)")
        return

if __name__ == '__main__':
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True, on_startup=set_commands)
