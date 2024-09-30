import asyncio
import random

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from config import TOKEN
import sqlite3
import logging
import requests

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Создание кнопок
button_registr = KeyboardButton(text="Регистрация в телеграм боте")
button_exchange_rates = KeyboardButton(text="Курс валют")
button_tips = KeyboardButton(text="Советы по экономии")
button_finances = KeyboardButton(text="Личные финансы")
button_view_expenses = KeyboardButton(text="Посмотреть расходы")

# Создание клавиатуры с кнопками
keyboards = ReplyKeyboardMarkup(keyboard=[
    [button_registr, button_exchange_rates],
    [button_tips, button_finances],
    [button_view_expenses]
], resize_keyboard=True)

# Подключение к базе данных
conn = sqlite3.connect('user.db')
cursor = conn.cursor()

# Создание таблицы, если она не существует
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
   id INTEGER PRIMARY KEY,
   telegram_id INTEGER UNIQUE,
   name TEXT,
   category1 TEXT,
   category2 TEXT,
   category3 TEXT,
   expenses1 REAL,
   expenses2 REAL,
   expenses3 REAL
)
''')

conn.commit()


# Определение состояний для ввода данных
class FinancesForm(StatesGroup):
    expenses1 = State()
    expenses2 = State()
    expenses3 = State()
    category1 = State()  # Состояние для ввода первой категории
    category2 = State()  # Состояние для ввода второй категории
    category3 = State()  # Состояние для ввода третьей категории


# Обработка команды /start
@dp.message(Command('start'))
async def send_start(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    cursor.execute('''SELECT * FROM users WHERE telegram_id = ?''', (telegram_id,))
    user = cursor.fetchone()

    if user:
        await message.answer(f"{message.from_user.full_name}, вы уже зарегистрированы!")
    else:
        await message.answer(
            f"Привет, {message.from_user.full_name}! Я ваш личный финансовый помощник. \nДавайте начнем с того, как назвать категории расходов.")
        await state.set_state(FinancesForm.category1)
        await message.answer("Введите название для первой категории:")


# Ввод первой категории
@dp.message(FinancesForm.category1)
async def set_category1(message: Message, state: FSMContext):
    category1 = message.text
    await state.update_data(category1=category1)
    await state.set_state(FinancesForm.category2)
    await message.answer("Введите название для второй категории:")


# Ввод второй категории
@dp.message(FinancesForm.category2)
async def set_category2(message: Message, state: FSMContext):
    category2 = message.text
    await state.update_data(category2=category2)
    await state.set_state(FinancesForm.category3)
    await message.answer("Введите название для третьей категории:")


# Ввод третьей категории и сохранение данных
@dp.message(FinancesForm.category3)
async def set_category3(message: Message, state: FSMContext):
    category3 = message.text
    data = await state.get_data()
    category1 = data['category1']
    category2 = data['category2']

    telegram_id = message.from_user.id
    name = message.from_user.full_name

    # Сохранение категорий и пользователя в базу данных
    cursor.execute('''
        INSERT INTO users (telegram_id, name, category1, category2, category3, expenses1, expenses2, expenses3)
        VALUES (?, ?, ?, ?, ?, 0, 0, 0)
    ''', (telegram_id, name, category1, category2, category3))
    conn.commit()

    await state.clear()
    await message.answer(
        f"Категории сохранены:\n1. {category1}\n2. {category2}\n3. {category3}\nТеперь вы можете начать вводить расходы. Для этого выберите одну из опций в меню:")


# Обработка команды регистрации (если нужно повторно)
@dp.message(F.text == "Регистрация в телеграм боте")
async def registration(message: Message):
    telegram_id = message.from_user.id
    name = message.from_user.full_name
    cursor.execute('''SELECT * FROM users WHERE telegram_id = ?''', (telegram_id,))
    user = cursor.fetchone()
    if user:
        await message.answer(f"{message.from_user.full_name}, вы уже зарегистрированы!")
    else:
        await message.answer(
            "Вы не зарегистрированы. Пожалуйста, введите команду /start, чтобы зарегистрироваться и указать категории.")


# Обработка команды для получения курса валют
@dp.message(F.text == "Курс валют")
async def exchange_rates(message: Message):
    url = "https://v6.exchangerate-api.com/v6/09edf8b2bb246e1f801cbfba/latest/USD"
    try:
        response = requests.get(url)
        data = response.json()
        if response.status_code != 200:
            await message.answer("Не удалось получить данные о курсе валют!")
            return
        usd_to_rub = data['conversion_rates']['RUB']
        eur_to_usd = data['conversion_rates']['EUR']
        euro_to_rub = eur_to_usd * usd_to_rub

        await message.answer(f"1 USD - {usd_to_rub:.2f} RUB\n1 EUR - {euro_to_rub:.2f} RUB")
    except:
        await message.answer("Произошла ошибка при получении курса валют!")

# Обработка команды для получения советов по экономии
@dp.message(F.text == "Советы по экономии")
async def send_tips(message: Message):
    tips = [
        "Совет 1: Ведите бюджет и следите за своими расходами.",
        "Совет 2: Откладывайте часть доходов на сбережения.",
        "Совет 3: Покупайте товары по скидкам и распродажам.",
        "Совет 4: Избегайте импульсивных покупок – давайте себе время на размышления перед каждой крупной покупкой.",
        "Совет 5: Используйте общественный транспорт или карпул, чтобы сократить расходы на бензин и обслуживание автомобиля.",
        "Совет 6: Планируйте покупки заранее и составляйте список перед походом в магазин, чтобы избежать лишних трат.",
        "Совет 7: Установите себе финансовые цели и откладывайте деньги на конкретные цели, такие как отпуск или крупные покупки.",
        "Совет 8: Используйте программы лояльности и кэшбэк-сервисы для экономии на повседневных расходах.",
        "Совет 9: Экономьте электроэнергию, выключая устройства, которые не используете, и используя энергосберегающие лампы.",
        "Совет 10: Готовьте еду дома – это поможет значительно сэкономить по сравнению с походами в кафе и рестораны.",
    ]
    tip = random.choice(tips)
    await message.answer(tip)

# Обработка команды для ввода и просмотра личных финансов
@dp.message(F.text == "Личные финансы")
async def finances(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    cursor.execute('''SELECT category1, category2, category3, expenses1, expenses2, expenses3 FROM users WHERE telegram_id = ?''', (telegram_id,))
    user = cursor.fetchone()

    if user:
        category1, category2, category3, expenses1, expenses2, expenses3 = user
        await message.answer(f"{message.from_user.full_name}, вот ваши текущие расходы:\n"
                             f"1. {category1} - текущие расходы: {expenses1} руб.\n"
                             f"2. {category2} - текущие расходы: {expenses2} руб.\n"
                             f"3. {category3} - текущие расходы: {expenses3} руб.")
        await state.set_state(FinancesForm.expenses1)
        await message.reply(f"Введите новые расходы для категории {category1}:")
    else:
        await message.answer("Категории расходов не найдены. Зарегистрируйтесь и введите категории.")

# Обработка ввода и добавления новых расходов для первой категории
@dp.message(FinancesForm.expenses1)
async def handle_expenses1(message: Message, state: FSMContext):
    try:
        new_expense = float(message.text)
        telegram_id = message.from_user.id
        cursor.execute('''SELECT expenses1, category1, category2 FROM users WHERE telegram_id = ?''', (telegram_id,))
        current_expense, category1, category2 = cursor.fetchone()
        updated_expense = current_expense + new_expense
        cursor.execute('''UPDATE users SET expenses1 = ? WHERE telegram_id = ?''', (updated_expense, telegram_id))
        conn.commit()
        await state.set_state(FinancesForm.expenses2)
        await message.reply(
            f"Новые расходы для категории {category1} успешно добавлены! Текущая сумма: {updated_expense} руб.\nВведите новые расходы для категории {category2}:")
    except ValueError:
        await message.reply("Пожалуйста, введите корректное число для расходов!")


# Обработка ввода и добавления новых расходов для второй категории
@dp.message(FinancesForm.expenses2)
async def handle_expenses2(message: Message, state: FSMContext):
    try:
        new_expense = float(message.text)
        telegram_id = message.from_user.id
        cursor.execute('''SELECT expenses2, category2, category3 FROM users WHERE telegram_id = ?''', (telegram_id,))
        current_expense, category2, category3 = cursor.fetchone()
        updated_expense = current_expense + new_expense
        cursor.execute('''UPDATE users SET expenses2 = ? WHERE telegram_id = ?''', (updated_expense, telegram_id))
        conn.commit()
        await state.set_state(FinancesForm.expenses3)
        await message.reply(
            f"Новые расходы для категории {category2} успешно добавлены! Текущая сумма: {updated_expense} руб.\nВведите новые расходы для категории {category3}:")
    except ValueError:
        await message.reply("Пожалуйста, введите корректное число для расходов!")


# Обработка ввода и добавления новых расходов для третьей категории
@dp.message(FinancesForm.expenses3)
async def handle_expenses3(message: Message, state: FSMContext):
    try:
        new_expense = float(message.text)
        telegram_id = message.from_user.id

        # Получаем текущие расходы и названия категорий
        cursor.execute('''SELECT expenses3, category3 FROM users WHERE telegram_id = ?''', (telegram_id,))
        current_expense3, category3 = cursor.fetchone()

        cursor.execute('''SELECT category1, category2, expenses1, expenses2 FROM users WHERE telegram_id = ?''',
                       (telegram_id,))
        category1, category2, expenses1, expenses2 = cursor.fetchone()

        # Обновляем расходы для третьей категории
        updated_expense3 = current_expense3 + new_expense
        cursor.execute('''UPDATE users SET expenses3 = ? WHERE telegram_id = ?''', (updated_expense3, telegram_id))
        conn.commit()

        # Очищаем состояние
        await state.clear()

        # Выводим сообщение о добавлении расходов
        await message.reply(
            f"Новые расходы для категории {category3} успешно добавлены! Текущая сумма: {updated_expense3} руб.")

        # Выводим текущие расходы для всех категорий
        await message.reply(f"{message.from_user.full_name}, ваши текущие расходы:\n"
                            f"1. {category1} - {expenses1} руб.\n"
                            f"2. {category2} - {expenses2} руб.\n"
                            f"3. {category3} - {updated_expense3} руб.")

    except ValueError:
        await message.reply("Пожалуйста, введите корректное число для расходов!")


# Кнопка для просмотра расходов
@dp.message(F.text == "Посмотреть расходы")
async def view_expenses(message: Message):
    telegram_id = message.from_user.id
    cursor.execute('''SELECT category1, expenses1, category2, expenses2, category3, expenses3 FROM users WHERE telegram_id = ?''', (telegram_id,))
    user = cursor.fetchone()
    if user:
        category1, expenses1, category2, expenses2, category3, expenses3 = user
        await message.answer(f"{message.from_user.full_name}, ваши расходы:\n"
                             f"1. {category1}: {expenses1} руб.\n"
                             f"2. {category2}: {expenses2} руб.\n"
                             f"3. {category3}: {expenses3} руб.")
    else:
        await message.answer("Данных о расходах не найдено. Зарегистрируйтесь и введите расходы.")

async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())