from aiogram import Router, types
from aiogram.filters import Text
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
import os
from datetime import datetime

router = Router()

@router.message(Text(text="💸 Начать Процессинг"))
async def start_processing(message: types.Message):
    image_path = os.path.join(os.path.dirname(__file__), "image4.png")
    image = FSInputFile(image_path)
    today = datetime.now().strftime("%d.%m.%Y")

    caption = (
        f"Курс на {today} - 10% 📈\n"
        "Кредитный лимит - 100.000₽ 💰\n"
        "Баланс - 0₽ 💵\n"
        "Продолжительность сеанса - 10~ минут ⏳\n\n"
        "Пожалуйста выберите платформу где хотите начать процессинг 🚀."
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔹1WIN", callback_data="process_1win"),
                InlineKeyboardButton(text="🐉Dragon Money", callback_data="process_dragon")
            ],
            [
                InlineKeyboardButton(text="♦️VAVADA", callback_data="process_vavada"),
                InlineKeyboardButton(text="🏠 Главное Меню", callback_data="main_menu")
            ],
            [
                InlineKeyboardButton(text="💳 Вывод средств", callback_data="withdraw"),
                InlineKeyboardButton(text="💸 Новый процессинг", callback_data="start_processing")
            ]
        ]
    )

    await message.answer_photo(photo=image, caption=caption, reply_markup=keyboard)

__all__ = ["router", "start_processing"]