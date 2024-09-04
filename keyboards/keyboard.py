from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup)
from aiogram.utils.keyboard import InlineKeyboardBuilder

def StartKeyboard():
    kb = [
        [InlineKeyboardButton(text="📜 Подивитися розклад", callback_data='DisplayTimetable')],
        [InlineKeyboardButton(text="🔗 Отримати посилання на пару", callback_data='GetLink')],
        [InlineKeyboardButton(text="📩 Пошти викладачів", callback_data='Emails')]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb)
    return keyboard

def AdminKeyboard(group_id: int):
    kb = [
        [InlineKeyboardButton(text="📜 Додати розклад", callback_data=f'AddTimetable_{group_id}')],
        [InlineKeyboardButton(text="🔗 Завантажити посилання на пару", callback_data=f'PushLink_{group_id}')],
        [InlineKeyboardButton(text="📩 Ввести пошти викладачів", callback_data=f'EnterEmails_{group_id}')],
        [InlineKeyboardButton(text="🤲 Передати права адміністратора", callback_data=f'ChangeAdmin_{group_id}')]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb)
    return keyboard

def DaysKeyboard(week: str, arg: str, type_user: str, group_id: int) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="1️⃣ Понеділок", callback_data=f'Monday_{week}_{type_user}_{group_id}')],
        [InlineKeyboardButton(text="2️⃣ Вівторок", callback_data=f'Tuesday_{week}_{type_user}_{group_id}')],
        [InlineKeyboardButton(text="3️⃣ Середа", callback_data=f'Wednesday_{week}_{type_user}_{group_id}')],
        [InlineKeyboardButton(text="4️⃣ Четвер", callback_data=f'Thursday_{week}_{type_user}_{group_id}')],
        [InlineKeyboardButton(text="5️⃣ П'ятниця", callback_data=f'Friday_{week}_{type_user}_{group_id}')],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=f"Back_{arg}_{type_user}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def WeeksKeyboard(arg: str, type_user: str, group_id: int) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="🔋 Верхній тиждень", callback_data=f'Top_Week_{type_user}_{group_id}')],
        [InlineKeyboardButton(text="🪫 Нижній тиждень", callback_data=f'Lower_Week_{type_user}_{group_id}')],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=f"Back_{arg}_{type_user}_{group_id}")]
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

def BackKb(arg: str, type_user: str, group_id: int):
    kb = [
        [InlineKeyboardButton(text="◀️ Назад", callback_data=f"Back_{arg}_{type_user}_{group_id}")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb)
    return keyboard

def ChangeAdminConfirmation(group_id: int):
    kb = [
        [InlineKeyboardButton(text="✅ Так, передати права", callback_data=f'ConfirmChange_{group_id}'), 
         InlineKeyboardButton(text="❌ Ні, скасувати дію", callback_data=f'CancelChange_{group_id}')]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)