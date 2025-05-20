import os
import sqlite3
import random
from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, Text
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
)

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Импортируем маршрутизатор и функцию процессинга из processing.py
from processing import router as processing_router, start_processing
dp.include_router(processing_router)

# Подключение к SQLite
conn = sqlite3.connect("users.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    start_date TEXT,
    credit_balance INTEGER DEFAULT 100000,
    available_balance INTEGER DEFAULT 0,
    status TEXT DEFAULT 'Новичок',
    processing_count INTEGER DEFAULT 0
)
""")
conn.commit()

# Клавиатура (основное меню)
keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🏠 Главное Меню"), KeyboardButton(text="💻 Личный Кабинет")],
        [KeyboardButton(text="💸 Начать Процессинг"), KeyboardButton(text="🧰 FAQ")]
    ],
    resize_keyboard=True
)

# Инлайн-клавиатуры для главного меню и FAQ
inline_main_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="💻 Личный Кабинет", callback_data="personal_cabinet"),
            InlineKeyboardButton(text="💸 Начать Процессинг", callback_data="start_processing")
        ],
        [InlineKeyboardButton(text="🧰 FAQ", callback_data="faq")]
    ]
)

faq_inline_buttons = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="🏠 Главное Меню", callback_data="main_menu"),
            InlineKeyboardButton(text="💻 Личный Кабинет", callback_data="personal_cabinet")
        ],
        [InlineKeyboardButton(text="💸 Начать Процессинг", callback_data="start_processing")]
    ]
)

# Функции работы с пользователем и БД

def generate_random_username():
    adjectives = ['fast', 'cool', 'brave', 'silent', 'wild', 'crazy']
    nouns = ['fox', 'tiger', 'eagle', 'panther', 'shark', 'lion']
    return f"#{random.choice(adjectives)}_{random.choice(nouns)}{random.randint(100, 999)}"

def get_display_name(user: types.User):
    return f"@{user.username}" if user.username else generate_random_username()

def register_user(user: types.User):
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user.id,))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users (user_id, username, start_date) VALUES (?, ?, ?)",
            (user.id, user.username or "", datetime.now().isoformat())
        )
        conn.commit()

def complete_processing(user_id: int):
    cursor.execute("SELECT processing_count, credit_balance, status FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if result is None:
        return 0, "Новичок", 100000
    current_count, current_limit, current_status = result
    current_count += 1

    # Определяем статус и кредитный лимит по новому количеству процессингов
    if current_count >= 20:
        new_status = "КИТ"
        credit_limit = 1_000_000
    elif current_count >= 10:
        new_status = "Про"
        credit_limit = 500_000
    elif current_count >= 5:
        new_status = "Стартер"
        credit_limit = 200_000
    else:
        new_status = "Новичок"
        credit_limit = 100_000

    # Начисляем 10% от лимита
    earned = int(credit_limit * 0.10)

    cursor.execute("""
        UPDATE users
        SET processing_count = ?,
            status = ?,
            credit_balance = ?,
            available_balance = available_balance + ?
        WHERE user_id = ?
    """, (current_count, new_status, credit_limit, earned, user_id))
    conn.commit()

    return earned, new_status, credit_limit

# Основные хэндлеры

@dp.message(Command(commands=["start"]))
async def cmd_start(message: types.Message):
    register_user(message.from_user)
    await button_main_menu(message)

@dp.message(Text(text="🏠 Главное Меню"))
async def button_main_menu(message: types.Message):
    register_user(message.from_user)
    display_name = get_display_name(message.from_user)
    text = (
        f"*Добро пожаловать, {display_name}!*\n\n"
        "ООО «OBNAL MSC» — признанный лидер рынка процессинга. "
        "У нас самые моментальные выплаты среди всех конкурентов, и самые большие проценты на рынке. "
        "Если хочешь получить свой M5 Competition — ты попал точно в цель. 🎯\n\n"
        "Изучи FAQ и начинай свой путь к финансовой свободе уже сегодня! 👊\n"
        "_«Проще чем с нами - ты нигде не заработаешь..»_"
    )
    photo = FSInputFile("image.png")
    await bot.send_photo(
        chat_id=message.chat.id,
        photo=photo,
        caption=text,
        parse_mode="Markdown",
        reply_markup=inline_main_menu
    )

async def show_personal_cabinet(source: types.Message | types.CallbackQuery):
    if isinstance(source, types.CallbackQuery):
        user = source.from_user
        chat_id = source.message.chat.id
    else:
        user = source.from_user
        chat_id = source.chat.id

    register_user(user)
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user.id,))
    row = cursor.fetchone()

    if not row:
        await source.answer("Пользователь не найден.")
        return

    display_name = get_display_name(user)
    start_date = datetime.fromisoformat(row[2])
    days = (datetime.now() - start_date).days + 1

    caption = (
        f"Ваш никнейм — {display_name}\n"
        f"Ваш стаж в проекте — {days} дн.\n"
        f"Ваш кредитный баланс — {row[3]:,}₽\n"
        f"Доступный вывод баланса — {row[4]:,}₽\n"
        f"Ваш статус — {row[5]}\n\n"
        "Ты только в начале своего пути.\n\n"
        "💬 «Секрет успеха — начать. Секрет начала — разбить сложное на простое и начать с первого шага.»"
    )
    photo = FSInputFile("image2.png")
    inline_buttons = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🏠 Главное Меню", callback_data="main_menu"),
                InlineKeyboardButton(text="🧰 FAQ", callback_data="faq")
            ],
            [InlineKeyboardButton(text="💸 Начать Процессинг", callback_data="start_processing")]
        ]
    )
    await bot.send_photo(
        chat_id=chat_id,
        photo=photo,
        caption=caption,
        reply_markup=inline_buttons
    )

@dp.message(Text(text="💻 Личный Кабинет"))
async def button_personal_cabinet(message: types.Message):
    await show_personal_cabinet(message)

@dp.callback_query(Text(text="personal_cabinet"))
async def inline_personal_cabinet_callback(callback: types.CallbackQuery):
    await show_personal_cabinet(callback)
    await callback.answer()

@dp.callback_query(Text(text="start_processing"))
async def inline_start_processing_callback(callback: types.CallbackQuery):
    # Перенаправляем на логику процессинга из processing.py
    await start_processing(callback.message)
    await callback.answer()

@dp.message(Text(text="🧰 FAQ"))
async def button_faq(message: types.Message):
    photo = FSInputFile("image3.png")
    caption = (
        "🧰 *Часто задаваемые вопросы:*\n\n"
        "1. *Как начать работать?*\n"
        "Мы используем мощность вашего устройства для процессинга — никакие реквизиты не требуются.\n\n"
        "2. *Как происходит вывод средств?*\n"
        "Вы получаете 10% от обналиченной суммы. Вывод возможен на карту или криптокошелек.\n\n"
        "3. *Какие риски существуют?*\n"
        "Никаких. Вы просто запускаете процессинг и получаете прибыль.\n\n"
        "Остались вопросы? Обращайтесь: @rudyzao"
    )
    await bot.send_photo(
        chat_id=message.chat.id,
        photo=photo,
        caption=caption,
        parse_mode="Markdown",
        reply_markup=faq_inline_buttons
    )

@dp.callback_query(Text(text="faq"))
async def faq_callback(callback: types.CallbackQuery):
    photo = FSInputFile("image3.png")
    caption = (
        "🧰 *Часто задаваемые вопросы:*\n\n"
        "1. *Как начать работать?*\n"
        "Мы используем мощность вашего устройства для процессинга — никакие реквизиты не требуются.\n\n"
        "2. *Как происходит вывод средств?*\n"
        "Вы получаете 10% от обналиченной суммы. Вывод возможен на карту или криптокошелек.\n\n"
        "3. *Какие риски существуют?*\n"
        "Никаких. Вы просто запускаете процессинг и получаете прибыль.\n\n"
        "Остались вопросы? Обращайтесь: @rudyzao"
    )
    await bot.send_photo(
        chat_id=callback.message.chat.id,
        photo=photo,
        caption=caption,
        parse_mode="Markdown",
        reply_markup=faq_inline_buttons
    )
    await callback.answer()

@dp.callback_query(Text(text="main_menu"))
async def inline_main_menu_callback(callback: types.CallbackQuery):
    await button_main_menu(callback.message)
    await callback.answer()

# Пример логики завершения процессинга с пошаговым редактированием сообщения
@dp.callback_query(lambda c: c.data.startswith("process_"))
async def processing_steps(callback: types.CallbackQuery):
    platform = callback.data.split("_")[1]  # platform: "1win", "dragon" или "vavada"
    await callback.answer()  # Быстрая реакция на нажатие

    msg = await callback.message.answer(f"🔄 Запуск процессинга на платформе {platform.upper()}...")

    steps = [
        "🔍 Анализируем платформу...",
        "📡 Устанавливаем соединение...",
        "🔒 Проверка безопасности...",
        "📊 Поиск транзакций...",
        "💸 Обработка данных...",
        "📤 Синхронизация с банком...",
        "✅ Финальная проверка..."
    ]
    # Задаём случайную длительность процессинга от 5 до 10 минут (300-600 секунд)
    total_duration = random.randint(300, 600)
    delay_per_step = total_duration // len(steps)

    for step in steps:
        await msg.edit_text(step)
        await asyncio.sleep(delay_per_step)

    # Завершаем процессинг: обновляем данные в БД, начисляем 10% от лимита
    user_id = callback.from_user.id
    earned, new_status, credit_limit = complete_processing(user_id)

    finish_text = (
        f"🎉 Процессинг завершён успешно!\n"
        f"💰 Вам начислено: {earned:,}₽ на баланс.\n"
        f"🏆 Ваш статус: {new_status}\n"
        f"💳 Ваш кредитный лимит теперь: {credit_limit:,}₽\n"
        f"📆 Время завершения: {datetime.now().strftime('%H:%M:%S')}\n\n"
        "Выберите, что хотите сделать дальше:"
    )
    await msg.edit_text(finish_text)

    # Предлагаем выбрать дальнейшие действия
    next_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💸 Новый процессинг", callback_data="start_processing")],
            [InlineKeyboardButton(text="💻 Личный Кабинет", callback_data="personal_cabinet")]
        ]
    )
    await callback.message.answer("✅ Выберите дальнейшее действие:", reply_markup=next_keyboard)

async def main():
    print("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())