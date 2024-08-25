from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup)

def StartKeyboard():
    kb = [
        [InlineKeyboardButton(text="📜 Подивитися розклад", callback_data='DisplayTimetable')],
        [InlineKeyboardButton(text="🔗 Отримати посилання на пару", callback_data='GetLink')],
        [InlineKeyboardButton(text="📩 Пошти викладачів", callback_data='Emails')]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb)
    return keyboard

def AdminKeyboard():
    kb = [
        [InlineKeyboardButton(text="📜 Додати розклад", callback_data='AddTimetable')],
        [InlineKeyboardButton(text="🔗 Завантажити посилання на пару", callback_data='PushLink')],
        [InlineKeyboardButton(text="📩 Ввести пошти викладачів", callback_data='EnterEmails')]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb)
    return keyboard

def DaysKeyboard(week: str, arg: str, type_user: str) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="1️⃣ Понеділок", callback_data=f'Monday_{week}_{type_user}')],
        [InlineKeyboardButton(text="2️⃣ Вівторок", callback_data=f'Tuesday_{week}_{type_user}')],
        [InlineKeyboardButton(text="3️⃣ Середа", callback_data=f'Wednesday_{week}_{type_user}')],
        [InlineKeyboardButton(text="4️⃣ Четвер", callback_data=f'Thursday_{week}_{type_user}')],
        [InlineKeyboardButton(text="5️⃣ П'ятниця", callback_data=f'Friday_{week}_{type_user}')],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=f"Back_{arg}_{type_user}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def WeeksKeyboard(arg: str, type_user: str) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="🔋 Верхній тиждень", callback_data=f'Top_Week_{type_user}')],
        [InlineKeyboardButton(text="🪫 Нижній тиждень", callback_data=f'Lower_Week_{type_user}')],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=f"Back_{arg}_{type_user}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def ConfirmationKeyboard() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="✅ Так", callback_data='Confirm'), 
         InlineKeyboardButton(text="❌ Ні", callback_data='Cancel')]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def ChooseAdmin_kb():
    kb = [
        [InlineKeyboardButton(text="💪 Я готовий", callback_data='YesIAm')]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb)
    return keyboard

def BackKb(arg: str, type_user: str):
    kb = [
        [InlineKeyboardButton(text="◀️ Назад", callback_data=f"Back_{arg}_{type_user}")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb)
    return keyboard