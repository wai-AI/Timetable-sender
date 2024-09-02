import asyncio #Імпорти
import logging
import sys
from typing import Any, Dict
import json
import time
import sqlite3
import requests
import datetime
import re

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup)

from keyboards.keyboard import(
    StartKeyboard,
    AdminKeyboard,
    DaysKeyboard,
    WeeksKeyboard,
    ConfirmationKeyboard,
    ChooseAdmin_kb,
    BackKb
)

from filters.chat_type import ChatTypeFilter

from aiogram.methods import LeaveChat
from aiogram.methods import SendMessage
from aiogram.types import FSInputFile, BufferedInputFile
from aiogram import Bot, Dispatcher, F, Router, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

form_router = Router() #Роутер

conn = sqlite3.connect("data.db")#Database
cursor = conn.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS KNEU (
    id                        INTEGER UNIQUE,
    chat_name                 TEXT,  
    timetable_monday_lower    TEXT    DEFAULT [Розкладу на понеділок нижнього тижня ще немає],
    timetable_tuesday_lower   TEXT    DEFAULT [Розкладу на вівторок нижнього тижня ще немає],
    timetable_wednesday_lower TEXT    DEFAULT [Розкладу на середу нижнього тижня ще немає],
    timetable_thursday_lower  TEXT    DEFAULT [Розкладу на четвер нижнього тижня ще немає],
    timetable_friday_lower    TEXT    DEFAULT [Розкладу на п'ятницю нижнього тижня ще немає],
    emails                    TEXT    DEFAULT [Пошти викладачів ще не додано],
    lessons                   TEXT    DEFAULT [Посилання на пари відсутні],
    admin_group               INTEGER,
    timetable_monday_top      TEXT    DEFAULT [Розкладу на понеділок верхнього тижня ще немає],
    timetable_tuesday_top     TEXT    DEFAULT [Розкладу на вівторок верхнього тижня ще немає],
    timetable_wednesday_top   TEXT    DEFAULT [Розкладу на середу верхнього тижня ще немає],
    timetable_thursday_top    TEXT    DEFAULT [Розкладу на четвер верхнього тижня ще немає],
    timetable_friday_top      TEXT    DEFAULT [Розкладу на п'ятницю верхнього тижня ще немає]
);""")

class Form(StatesGroup): #Клас зі стейтами
    MondayTimetable = State()
    TuesdayTimetable = State()
    WednesdayTimetable = State()
    ThursdayTimetable = State()
    FridayTimetable = State()

    GroupId = State()

    Links = State()

    Emails = State()

with open('settings.json', 'r') as json_file: #Вигрузка з конфігу та визначення змінних
    config = json.load(json_file)
TOKEN = config['TOKEN']

def telegraph_file_upload(path_to_file):  #Завантаження медіа на телеграф
    '''
    Sends a file to telegra.ph storage and returns its url
    Works ONLY with 'gif', 'jpeg', 'jpg', 'png', 'mp4' 
    
    Parameters
    ---------------
    path_to_file -> str, path to a local file
    
    Return
    ---------------
    telegraph_url -> str, url of the file uploaded

    >>>telegraph_file_upload('test_image.jpg')
    https://telegra.ph/file/16016bafcf4eca0ce3e2b.jpg    
    >>>telegraph_file_upload('untitled.txt')
    error, txt-file can not be processed
    '''
    file_types = {'gif': 'image/gif', 'jpeg': 'image/jpeg', 'jpg': 'image/jpg', 'png': 'image/png', 'mp4': 'video/mp4'}
    file_ext = path_to_file.split('.')[-1]
    
    if file_ext in file_types:
        file_type = file_types[file_ext]
    else:
        return f'error, {file_ext}-file can not be proccessed' 
      
    with open(path_to_file, 'rb') as f:
        url = 'https://telegra.ph/upload'
        response = requests.post(url, files={'file': ('file', f, file_type)}, timeout=20)
    
    telegraph_url = json.loads(response.content)
    telegraph_url = telegraph_url[0]['src']
    telegraph_url = f'https://telegra.ph{telegraph_url}'
    return telegraph_url

def format_message_with_bold(message: str) -> str:
    pattern = r'^(.*?) - (https?://[^\s]+)$'
    
    formatted_lines = []
    is_valid = True

    lines = message.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        match = re.match(pattern, line)
        if match:
            subject = match.group(1)
            link = match.group(2)
            bold_part = f"<b>{subject}</b>"
            formatted_line = f"{bold_part} - <a href='{link}'>Перейти</a>"
            formatted_lines.append(formatted_line)
        else:
            is_valid = False
            formatted_lines.append(line)

    formatted_message = '\n'.join(formatted_lines)
    
    return is_valid, formatted_message

def format_and_check_message(message: str) -> str:
    pattern = r'^[^\s]+( [^\s]+)* - [a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    
    formatted_lines = []
    is_valid = True

    lines = message.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if re.match(pattern, line):
            parts = line.split(' - ', 1)
            bold_part = f"<b>{parts[0]}</b>"
            email_part = parts[1]
            formatted_line = f"{bold_part} - {email_part}"
            formatted_lines.append(formatted_line)
        else:
            is_valid = False
            formatted_lines.append(line)

    formatted_message = '\n'.join(formatted_lines)
    
    return is_valid, formatted_message

def ChatsList(id_user: int):
    kb = InlineKeyboardBuilder()
    cursor.execute("""SELECT id FROM KNEU WHERE admin_group = ?""", (id_user,))
    chats_name = cursor.fetchall()

    for index in chats_name:
        id_chat = index[0]
        kb.button(text=f"{id_chat}", callback_data=f"id_chat_{id_chat}")
    
    kb.button(text=f"◀️ Назад", callback_data="MainMenu")
    return kb.adjust(1).as_markup(resize_keyboard=True)

async def DownloadingPhotos(message: Message) -> tuple[str, str]:
    if message.photo:
        user_id = message.from_user.id
        file_id = message.photo[-1].file_id
        file_info = await message.bot.get_file(file_id)
        path = "C:\\Users\\Pavel\\Desktop\\Homework\\Codes\\Python\\Timetable-sender\\pic\\picture.png"
        await message.bot.download_file(file_info.file_path, destination=path)

        return path
    return None

async def get_admin_groups(user_id):
    cursor.execute('''SELECT id, chat_name FROM KNEU WHERE admin_group = ?''', (user_id,))
    groups = cursor.fetchall()  # Повертає список кортежів (id, chat_name)
    return groups

@form_router.message(Command("configure"), ChatTypeFilter(chat_type=['private']))
async def AdminMessage(message: Message) -> None:
    user_id = message.from_user.id
    groups = await get_admin_groups(user_id)

    if not groups:  # Якщо у користувача немає груп
        await message.answer("Ви не є адміністратором жодної з груп. Якщо бажаєте стати адміністратором - додайте бота до своєї групи.")
        return

    keyboard = InlineKeyboardBuilder()
    for group_id, chat_name in groups:
        keyboard.add(
            InlineKeyboardButton(text=f"Група {chat_name}", callback_data=f"configure_group_{group_id}")
        )

    await message.answer("Оберіть групу для налаштування:", reply_markup=keyboard.as_markup())

@form_router.callback_query(lambda call: call.data.startswith("configure_group_"))
async def configure_selected_group(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    group_id = int(call.data.split("_")[-1])
    cursor.execute("""SELECT chat_name FROM KNEU WHERE id = ?""", (group_id,))
    res = cursor.fetchone()
    chat_name = res[0]

    await state.update_data(selected_group=group_id)
    
    await call.message.answer(f"Ви обрали групу <b>{chat_name}</b>. Тепер ви можете виконувати налаштування.", reply_markup=AdminKeyboard(group_id))

@form_router.message(Command("configure"), ChatTypeFilter(chat_type = ["group", "supergroup"]))
async def AdminMessage(message: Message) -> None:
    await message.answer("Налаштування боту доступне лише в приватних повідомленнях. Будь ласка, перейдіть до чату з ботом та повторіть цю команду")

@form_router.message(CommandStart(), ChatTypeFilter(chat_type = ["group", "supergroup"]))
async def StartMessage(message: Message, state: FSMContext) -> None:
    id_chat = message.chat.id

    cursor.execute("""SELECT id FROM KNEU""")
    chats = cursor.fetchall()

    chats_ids = [chat[0] for chat in chats] 

    if id_chat not in chats_ids:
        await message.answer("Вашої групи не має в базі. Бажаєте додати?", reply_markup=ConfirmationKeyboard())
        return
    else:
        await message.answer("Оберіть функцію", reply_markup=StartKeyboard())

@form_router.message(CommandStart(), ChatTypeFilter(chat_type = ["private"]))
async def CancelStart(message: Message):
    await message.answer("Дана команда працює лише в групових чатах")

@form_router.callback_query(lambda call: call.data == 'Confirm')
async def ConfirmAdd(call: CallbackQuery, state: FSMContext) -> None:
    await call.message.delete()
    id_chat = call.message.chat.id
    id_user = call.from_user.id
    name_chat = call.message.chat.full_name

    await state.update_data(GroupId=id_chat, UserId=id_user)
    cursor.execute("""INSERT INTO KNEU (id, chat_name) VALUES (?,?)""", (id_chat, name_chat,))
    conn.commit()
    
    await state.update_data(GroupId=id_chat)
    await call.message.answer('''Вашу групу успішно додано до бази. Тепер оберіть людину, яка буде наповнювати мене актуальною інформацією про розклад занять, посилання на пари та пошти викладачів''', reply_markup=ChooseAdmin_kb())

@form_router.callback_query(lambda call: call.data == 'Cancel')
async def decline_add(call: CallbackQuery) -> None:
    chat_id = call.message.chat.id
    await call.message.delete()
    await call.message.answer("""Вас зрозумів 🫡\nЯк знадоблюся - Ви завжди можете додати мене назад до чату""")
    await call.bot.leave_chat(chat_id)


@form_router.callback_query(lambda call: call.data == 'YesIAm')
async def ChooseAdmin(call: CallbackQuery) -> None:
    await call.message.delete()
    id_user = call.from_user.id
    admin_user_name = call.from_user.full_name
    id_group = call.message.chat.id
    print(id_user)

    cursor.execute('''UPDATE KNEU SET admin_group = ? WHERE id = ?''', (id_user, id_group,))
    conn.commit()

    await call.message.answer(f"Вітаю, адміністратора обрано (<b>{admin_user_name}</b>). Перейдіть до мене в особисті повідомлення та відправте команду /configure")
    await call.bot.send_message(id_user, "Вітаю, тепер ви - адміністратор. Для налаштування бота введіть команду /configure")

@form_router.callback_query(F.data.startswith('AddTimetable_'))
async def SetTimetable(call: CallbackQuery, state: FSMContext) -> None:
    parts = call.data.split('_')
    _, group_id = parts

    await call.message.delete()
    await call.message.answer("Оберіть тиждень", reply_markup=WeeksKeyboard('MainMenu', 'Admin', group_id))

@form_router.callback_query(F.data.startswith('Top_Week') | F.data.startswith('Lower_Week'))
async def SetTimetable(call: CallbackQuery, state: FSMContext) -> None:
    parts = call.data.rsplit('_', 2)
    action, type_user, group_id = parts

    if action == 'Top_Week':
        if type_user == 'Admin':
            await call.message.delete()
            await call.message.answer("Ви обрали верхній тиждень", reply_markup=DaysKeyboard('Top', 'WeekSelection', 'Admin', group_id))
        elif type_user == 'User':
            await call.message.delete()
            await call.message.answer("Ви обрали верхній тиждень. Оберіть день, розклад якого Вас цікавить", reply_markup=DaysKeyboard('Top', 'WeekSelection', 'User', group_id))
    elif action == 'Lower_Week':
        if type_user == 'Admin':
            await call.message.delete()
            await call.message.answer("Ви обрали нижній тиждень", reply_markup=DaysKeyboard('Lower', 'WeekSelection', 'Admin', group_id))
        elif type_user == 'User':
            await call.message.delete()
            await call.message.answer("Ви обрали нижній тиждень. Оберіть день, розклад якого Вас цікавить", reply_markup=DaysKeyboard('Lower', 'WeekSelection', 'User', group_id))
    else:
        await call.message.answer("Невідомий вибір. Спробуйте ще раз.")

@form_router.callback_query(F.data.startswith('Monday_'))
async def SetMondayTimetable(call: CallbackQuery, state: FSMContext) -> None:
    parts = call.data.split('_')

    _, action, type_user, id_group = parts

    await state.update_data(action=action)
    await state.update_data(type_user=type_user)
    await state.update_data(id_group=id_group)
    await call.message.delete()

    if action == 'Lower':
        if type_user == 'Admin':
            await state.set_state(Form.MondayTimetable)
            await call.message.answer("Відправте розклад на понеділок нижнього тижня", reply_markup=BackKb('WeekSelection', 'Admin'))
        elif type_user == 'User':
            id_group = call.message.chat.id
            cursor.execute("""SELECT timetable_monday_lower FROM KNEU WHERE id = ?""", (id_group,))
            result = cursor.fetchone()
            timetable = result[0]

            if timetable == "Розкладу на понеділок нижнього тижня ще немає":
                await call.message.answer(f'<b>{timetable}</b>', reply_markup=BackKb('WeekSelection', 'User'))
            else:
                await call.message.answer(f'<a href="{timetable}"> </a><b>Розклад на понеділок нижнього тижня</b>', reply_markup=BackKb('WeekSelection', 'User'))
    elif action == "Top":
        if type_user == 'Admin':
            await state.set_state(Form.MondayTimetable)
            await call.message.answer("Відправте розклад на понеділок верхнього тижня", reply_markup=BackKb('WeekSelection', 'Admin'))
        elif type_user == 'User':
            id_group = call.message.chat.id
            cursor.execute("""SELECT timetable_monday_top FROM KNEU WHERE id = ?""", (id_group,))
            result = cursor.fetchone()
            timetable = result[0]

            if timetable == "Розкладу на понеділок верхнього тижня ще немає":
                await call.message.answer(f'<b>{timetable}</b>', reply_markup=BackKb('WeekSelection', 'User'))
            else:
                await call.message.answer(f'<a href="{timetable}"> </a><b>Розклад на понеділок верхнього тижня</b>', reply_markup=BackKb('WeekSelection', 'User'))

@form_router.message(Form.MondayTimetable)
async def SetMonday(message: Message, state: FSMContext) -> None:
    if not message.photo:
        await message.answer("Будь ласка, надішліть розклад як фото", reply_markup=BackKb('WeekSelection', 'Admin'))
        return
    
    path = await DownloadingPhotos(message)
    
    data = await state.get_data()
    action = data.get('action')
    id_group = data.get('id_group')

    if path and id_group:
        url = telegraph_file_upload(path)
        await state.update_data(MondayTimetable=url)
        if action == "Lower":
            cursor.execute("""UPDATE KNEU SET timetable_monday_lower = ? WHERE id = ?""", (url, id_group))
            conn.commit()
            await message.answer(f"Розклад на понеділок нижнього тижня успішно збережено", reply_markup=DaysKeyboard('Lower', 'WeekSelection', 'Admin', id_group))
        elif action == "Top":
            cursor.execute("""UPDATE KNEU SET timetable_monday_top = ? WHERE id = ?""", (url, id_group))
            conn.commit()
            await message.answer(f"Розклад на понеділок верхнього тижня успішно збережено", reply_markup=DaysKeyboard('Top','WeekSelection', 'Admin', id_group))
        else:
            await message.answer(f"Виникла помилка")
    else:
        await message.answer("Адміністратор не знайдений у базі даних або файл не був завантажений.")

@form_router.callback_query(F.data.startswith('Tuesday_'))
async def SetTuesdayTimetable(call: CallbackQuery, state: FSMContext) -> None:
    parts = call.data.split('_')

    _, action, type_user, id_group = parts

    await state.update_data(action=action)
    await state.update_data(type_user=type_user)
    await state.update_data(id_group=id_group)
    await call.message.delete()

    if action == 'Lower':
        if type_user == 'Admin':
            await state.set_state(Form.TuesdayTimetable)
            await call.message.answer("Відправте розклад на вівторок нижнього тижня", reply_markup=BackKb('WeekSelection', 'Admin'))
        elif type_user == 'User':
            id_group = call.message.chat.id
            cursor.execute("""SELECT timetable_tuesday_lower FROM KNEU WHERE id = ?""", (id_group,))
            result = cursor.fetchone()
            timetable = result[0]

            if timetable == "Розкладу на вівторок нижнього тижня ще немає":
                await call.message.answer(f'<b>{timetable}</b>', reply_markup=BackKb('WeekSelection', 'User'))
            else:
                await call.message.answer(f'<a href="{timetable}"> </a><b>Розклад на вівторок нижнього тижня</b>', reply_markup=BackKb('WeekSelection', 'User'))
    elif action == "Top":
        if type_user == 'Admin':
            await state.set_state(Form.TuesdayTimetable)
            await call.message.answer("Відправте розклад на вівторок верхнього тижня", reply_markup=BackKb('WeekSelection', 'Admin'))
        elif type_user == 'User':
            id_group = call.message.chat.id
            cursor.execute("""SELECT timetable_tuesday_top FROM KNEU WHERE id = ?""", (id_group,))
            result = cursor.fetchone()
            timetable = result[0]

            if timetable == "Розкладу на вівторок верхнього тижня ще немає":
                await call.message.answer(f'<b>{timetable}</b>', reply_markup=BackKb('WeekSelection', 'User'))
            else:
                await call.message.answer(f'<a href="{timetable}"> </a><b>Розклад на вівторок верхнього тижня</b>', reply_markup=BackKb('WeekSelection', 'User'))

@form_router.message(Form.TuesdayTimetable)
async def SetTuesday(message: Message, state: FSMContext) -> None:
    if not message.photo:
        await message.answer("Будь ласка, надішліть розклад як фото", reply_markup=BackKb('WeekSelection', 'Admin'))
        return
    path = await DownloadingPhotos(message)
    
    data = await state.get_data()
    action = data.get('action')
    id_group = data.get('id_group')

    if path and id_group:
        url = telegraph_file_upload(path)
        await state.update_data(TuesdayTimetable=url)
        if action == "Lower":
            cursor.execute("""UPDATE KNEU SET timetable_tuesday_lower = ? WHERE id = ?""", (url, id_group))
            conn.commit()
            await message.answer(f"Розклад на вівторок нижнього тижня успішно збережено", reply_markup=DaysKeyboard('Lower', 'WeekSelection', 'Admin', id_group))
        elif action == "Top":
            cursor.execute("""UPDATE KNEU SET timetable_tuesday_top = ? WHERE id = ?""", (url, id_group))
            conn.commit()
            await message.answer(f"Розклад на вівторок верхнього тижня успішно збережено", reply_markup=DaysKeyboard('Top','WeekSelection', 'Admin', id_group))
        else:
            await message.answer(f"Виникла помилка")
    else:
        await message.answer("Адміністратор не знайдений у базі даних або файл не був завантажений.")

@form_router.callback_query(F.data.startswith('Wednesday_'))
async def SetWednesdayTimetable(call: CallbackQuery, state: FSMContext) -> None:
    parts = call.data.split('_')

    _, action, type_user, id_group = parts

    await state.update_data(action=action)
    await state.update_data(type_user=type_user)
    await state.update_data(id_group=id_group)
    await call.message.delete()

    if action == 'Lower':
        if type_user == 'Admin':
            await state.set_state(Form.WednesdayTimetable)
            await call.message.answer("Відправте розклад на середу нижнього тижня", reply_markup=BackKb('WeekSelection', 'Admin'))
        elif type_user == 'User':
            id_group = call.message.chat.id
            cursor.execute("""SELECT timetable_wednesday_lower FROM KNEU WHERE id = ?""", (id_group,))
            result = cursor.fetchone()
            timetable = result[0]

            if timetable == "Розкладу на середу нижнього тижня ще немає":
                await call.message.answer(f'<b>{timetable}</b>', reply_markup=BackKb('WeekSelection', 'User'))
            else:
                await call.message.answer(f'<a href="{timetable}"> </a><b>Розклад на середу нижнього тижня</b>', reply_markup=BackKb('WeekSelection', 'User'))
    elif action == "Top":
        if type_user == 'Admin':
            await state.set_state(Form.WednesdayTimetable)
            await call.message.answer("Відправте розклад на середу верхнього тижня", reply_markup=BackKb('WeekSelection', 'Admin'))
        elif type_user == 'User':
            id_group = call.message.chat.id
            cursor.execute("""SELECT timetable_wednesday_top FROM KNEU WHERE id = ?""", (id_group,))
            result = cursor.fetchone()
            timetable = result[0]

            if timetable == "Розкладу на середу верхнього тижня ще немає":
                await call.message.answer(f'<b>{timetable}</b>', reply_markup=BackKb('WeekSelection', 'User'))
            else:
                await call.message.answer(f'<a href="{timetable}"> </a><b>Розклад на середу верхнього тижня</b>', reply_markup=BackKb('WeekSelection', 'User'))

@form_router.message(Form.WednesdayTimetable)
async def SetWednesday(message: Message, state: FSMContext) -> None:
    if not message.photo:
        await message.answer("Будь ласка, надішліть розклад як фото", reply_markup=BackKb('WeekSelection', 'Admin'))
        return
    path = await DownloadingPhotos(message)
    
    data = await state.get_data()
    action = data.get('action')
    id_group = data.get('id_group')

    if path and id_group:
        url = telegraph_file_upload(path)
        await state.update_data(WednesdayTimetable=url)
        if action == "Lower":
            cursor.execute("""UPDATE KNEU SET timetable_wednesday_lower = ? WHERE id = ?""", (url, id_group))
            conn.commit()
            await message.answer(f"Розклад на середу нижнього тижня успішно збережено", reply_markup=DaysKeyboard('Lower', 'WeekSelection', 'Admin', id_group))
        elif action == "Top":
            cursor.execute("""UPDATE KNEU SET timetable_wednesday_top = ? WHERE id = ?""", (url, id_group))
            conn.commit()
            await message.answer(f"Розклад на середу верхнього тижня успішно збережено", reply_markup=DaysKeyboard('Top','WeekSelection', 'Admin', id_group))
        else:
            await message.answer(f"Виникла помилка")
    else:
        await message.answer("Адміністратор не знайдений у базі даних або файл не був завантажений.")

@form_router.callback_query(F.data.startswith('Thursday_'))
async def SetThursdayTimetable(call: CallbackQuery, state: FSMContext) -> None:
    parts = call.data.split('_')

    _, action, type_user, id_group = parts

    await state.update_data(action=action)
    await state.update_data(type_user=type_user)
    await state.update_data(id_group=id_group)
    await call.message.delete()

    if action == 'Lower':
        if type_user == 'Admin':
            await state.set_state(Form.ThursdayTimetable)
            await call.message.answer("Відправте розклад на четвер нижнього тижня", reply_markup=BackKb('WeekSelection', 'Admin'))
        elif type_user == 'User':
            id_group = call.message.chat.id
            cursor.execute("""SELECT timetable_thursday_lower FROM KNEU WHERE id = ?""", (id_group,))
            result = cursor.fetchone()
            timetable = result[0]

            if timetable == "Розкладу на четвер нижнього тижня ще немає":
                await call.message.answer(f'<b>{timetable}</b>', reply_markup=BackKb('WeekSelection', 'User'))
            else:
                await call.message.answer(f'<a href="{timetable}"> </a><b>Розклад на четвер нижнього тижня</b>', reply_markup=BackKb('WeekSelection', 'User'))
    elif action == "Top":
        if type_user == 'Admin':
            await state.set_state(Form.ThursdayTimetable)
            await call.message.answer("Відправте розклад на четвер верхнього тижня", reply_markup=BackKb('WeekSelection', 'Admin'))
        elif type_user == 'User':
            id_group = call.message.chat.id
            cursor.execute("""SELECT timetable_thursday_top FROM KNEU WHERE id = ?""", (id_group,))
            result = cursor.fetchone()
            timetable = result[0]

            if timetable == "Розкладу на четвер верхнього тижня ще немає":
                await call.message.answer(f'<b>{timetable}</b>', reply_markup=BackKb('WeekSelection', 'User'))
            else:
                await call.message.answer(f'<a href="{timetable}"> </a><b>Розклад на четвер верхнього тижня</b>', reply_markup=BackKb('WeekSelection', 'User'))

@form_router.message(Form.ThursdayTimetable)
async def SetThursday(message: Message, state: FSMContext) -> None:
    if not message.photo:
        await message.answer("Будь ласка, надішліть розклад як фото", reply_markup=BackKb('WeekSelection', 'Admin'))
        return
    path = await DownloadingPhotos(message)
    
    data = await state.get_data()
    action = data.get('action')
    id_group = data.get('id_group')

    if path and id_group:
        url = telegraph_file_upload(path)
        await state.update_data(ThursdayTimetable=url)
        if action == "Lower":
            cursor.execute("""UPDATE KNEU SET timetable_thursday_lower = ? WHERE id = ?""", (url, id_group))
            conn.commit()
            await message.answer(f"Розклад на четвер нижнього тижня успішно збережено", reply_markup=DaysKeyboard('Lower', 'WeekSelection', 'Admin', id_group))
        elif action == "Top":
            cursor.execute("""UPDATE KNEU SET timetable_thursday_top = ? WHERE id = ?""", (url, id_group))
            conn.commit()
            await message.answer(f"Розклад на четвер верхнього тижня успішно збережено", reply_markup=DaysKeyboard('Top','WeekSelection', 'Admin', id_group))
        else:
            await message.answer(f"Виникла помилка")
    else:
        await message.answer("Адміністратор не знайдений у базі даних або файл не був завантажений.")

@form_router.callback_query(F.data.startswith('Friday_'))
async def SetFridayTimetable(call: CallbackQuery, state: FSMContext) -> None:
    parts = call.data.split('_')

    _, action, type_user, id_group = parts

    await state.update_data(action=action)
    await state.update_data(type_user=type_user)
    await state.update_data(id_group=id_group)
    await call.message.delete()

    if action == 'Lower':
        if type_user == 'Admin':
            await state.set_state(Form.FridayTimetable)
            await call.message.answer("Відправте розклад на п'ятницю нижнього тижня", reply_markup=BackKb('WeekSelection', 'Admin'))
        elif type_user == 'User':
            id_group = call.message.chat.id
            cursor.execute("""SELECT timetable_friday_lower FROM KNEU WHERE id = ?""", (id_group,))
            result = cursor.fetchone()
            timetable = result[0]

            if timetable == "Розкладу на п'ятницю нижнього тижня ще немає":
                await call.message.answer(f'<b>{timetable}</b>', reply_markup=BackKb('WeekSelection', 'User'))
            else:
                await call.message.answer(f"<a href='{timetable}'> </a><b>Розклад на п'ятницю нижнього тижня</b>", reply_markup=BackKb('WeekSelection', 'User'))
    elif action == "Top":
        if type_user == 'Admin':
            await state.set_state(Form.FridayTimetable)
            await call.message.answer("Відправте розклад на п'ятницю верхнього тижня", reply_markup=BackKb('WeekSelection', 'Admin'))
        elif type_user == 'User':
            id_group = call.message.chat.id
            cursor.execute("""SELECT timetable_friday_top FROM KNEU WHERE id = ?""", (id_group,))
            result = cursor.fetchone()
            timetable = result[0]

            if timetable == "Розкладу на п'ятницю верхнього тижня ще немає":
                await call.message.answer(f'<b>{timetable}</b>', reply_markup=BackKb('WeekSelection', 'User'))
            else:
                await call.message.answer(f"<a href='{timetable}'> </a><b>Розклад на п'ятницю верхнього тижня</b>", reply_markup=BackKb('WeekSelection', 'User'))

@form_router.message(Form.FridayTimetable)
async def SetFriday(message: Message, state: FSMContext) -> None:
    if not message.photo:
        await message.answer("Будь ласка, надішліть розклад як фотографію", reply_markup=BackKb('WeekSelection', 'Admin'))
        return
    path = await DownloadingPhotos(message)
    
    data = await state.get_data()
    action = data.get('action')
    id_group = data.get('id_group')

    if path and id_group:
        url = telegraph_file_upload(path)
        await state.update_data(FridayTimetable=url)
        if action == "Lower":
            cursor.execute("""UPDATE KNEU SET timetable_friday_lower = ? WHERE id = ?""", (url, id_group))
            conn.commit()
            await message.answer(f"Розклад на п'ятницю нижнього тижня успішно збережено", reply_markup=DaysKeyboard('Lower', 'WeekSelection', 'Admin', id_group))
        elif action == "Top":
            cursor.execute("""UPDATE KNEU SET timetable_friday_top = ? WHERE id = ?""", (url, id_group))
            conn.commit()
            await message.answer(f"Розклад на п'ятницю верхнього тижня успішно збережено", reply_markup=DaysKeyboard('Top','WeekSelection', 'Admin', id_group))
        else:
            await message.answer(f"Виникла помилка")
    else:
        await message.answer("Адміністратор не знайдений у базі даних або файл не був завантажений.")

@form_router.callback_query(F.data.startswith('PushLink_'))
async def SetLinks(call: CallbackQuery, state: FSMContext) -> None:
    parts = call.data.split('_')
    _, group_id = parts

    await state.set_state(Form.Links)
    await state.update_data(id_group=group_id)
    await call.message.delete()
    await call.message.answer("Окей. Відправте список предметів та посилань на їх пари. Будь ласка, слідуйте наступному формату:\n\nДисципліна1 - Посилання1\nДисципліна2 - Посилання2", reply_markup=BackKb('MainMenu','Admin'))

@form_router.message(Form.Links)
async def CheckLinks(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Будь ласка, надішліть список предметів та посилань на їх пари в форматі:\n\nДисципліна1 - Посилання1\nДисципліна2 - Посилання2", reply_markup=BackKb('MainMenu','Admin'))
        return
    id_user = message.from_user.id
    data = await state.get_data()
    id_group = data.get("id_group")

    print(id_group)

    if not id_group:
        await message.answer("Сталася помилка: не вдалося визначити ідентифікатор групи")
        return
    
    text_message = message.text

    is_valid, formatted_message = format_message_with_bold(text_message)
    
    if is_valid:
        await state.update_data(Links=text_message)
        try:
            cursor.execute("""UPDATE KNEU SET lessons = ? WHERE id = ?""", (text_message, id_group,))
            conn.commit()
            await message.answer("Посилання на пари успішно збережені")
            await message.answer(formatted_message)
            await message.answer("Оберіть дію", reply_markup=AdminKeyboard(id_group))
        except Exception as e:
            await message.answer(f"Сталася помилка при збереженні даних: <code>{str(e)}</code>")
    else:
        await message.answer("Введені вами дані не відповідають вказаному формату. Будь ласка, спробуйте знову", reply_markup=BackKb('MainMenu','Admin'))

@form_router.callback_query(F.data.startswith('EnterEmails_'))
async def SetEmails(call: CallbackQuery, state: FSMContext) -> None:
    parts = call.data.split('_')
    _, group_id = parts
    
    await state.set_state(Form.Emails)
    await state.update_data(id_group=group_id)
    await call.message.delete()
    await call.message.answer("Окей. Відправте список дисциплін та пошти викладачів, які їх ведуть. Будь ласка, слідуйте наступному формату:\n\nДисципліна1 - Пошта1\nДисципліна2 - Пошта2", reply_markup=BackKb('MainMenu','Admin'))

@form_router.message(Form.Emails)
async def CheckEmails(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Будь ласка, надішліть список предметів та посилань на їх пари в форматі:\n\nДисципліна1 - Пошта1\nДисципліна2 - Пошта2", reply_markup=BackKb('MainMenu','Admin'))
        return
    text_message = message.text

    id_user = message.from_user.id
    data = await state.get_data()
    id_group = data.get("id_group")

    is_valid, formatted_message = format_and_check_message(text_message)

    if is_valid:
        if not id_group:
            await message.answer("Виникла помилка: ідентифікатор групи не знайдено.")
            return
        await state.update_data(Links=text_message)
        
        try:
            cursor.execute("""UPDATE KNEU SET emails = ? WHERE id = ?""", (text_message, id_group,))
            conn.commit()
            await message.answer("Пошти викладачів успішно збережені")
            await message.answer(formatted_message, parse_mode='HTML')
            await message.answer("Оберіть дію", reply_markup=AdminKeyboard(id_group))
        except Exception as e:
            await message.answer(f"Виникла помилка при збереженні данних: {str(e)}")
    else:
        await message.answer("Введені вами дані не відповідають формату 'Текст - Email'. Будь ласка, спробуйте знову.", reply_markup=BackKb('MainMenu','Admin'))

@form_router.callback_query(lambda call: call.data == "DisplayTimetable")
async def GetTimetable(call: CallbackQuery, state: FSMContext) -> None:
    id_group = call.message.chat.id
    await call.message.delete()
    await call.message.answer("Оберіть тиждень", reply_markup=WeeksKeyboard('MainMenu', 'User', id_group))

@form_router.callback_query(lambda call: call.data == "GetLink")
async def GetLinks(call: CallbackQuery, state: FSMContext) -> None:
    id_group = call.message.chat.id
    await call.message.delete()
    
    cursor.execute("SELECT lessons FROM KNEU WHERE id = ?", (id_group,))
    result = cursor.fetchone()
    lessons = result[0]

    is_valid, formatted_message = format_message_with_bold(lessons)

    await call.message.answer(f"<b>Посилання на пари:</b>\n\n{formatted_message}", reply_markup=BackKb('MainMenu', 'User'))

@form_router.callback_query(lambda call: call.data == "Emails")
async def GetEmails(call: CallbackQuery, state: FSMContext) -> None:
    id_group = call.message.chat.id
    await call.message.delete()
    
    cursor.execute("SELECT emails FROM KNEU WHERE id = ?", (id_group,))
    result = cursor.fetchone()
    emails = result[0]

    is_valid, formatted_message = format_and_check_message(emails)

    await call.message.answer(f"<b>Пошти викладачів:</b>\n\n{formatted_message}", reply_markup=BackKb('MainMenu', 'User'))

@form_router.callback_query(F.data.startswith('Back_'))
async def Back(call: CallbackQuery, state: FSMContext) -> None:
    parts = call.data.split('_')

    _, action, type_user = parts
    await call.message.delete()
    
    data = await state.get_data()
    group_id = data.get('id_group')

    if action == "WeekSelection":
        if type_user == 'Admin':
 
            await call.message.answer("Оберіть тиждень", reply_markup=WeeksKeyboard('MainMenu', 'Admin', group_id))
        elif type_user == 'User':
            id_group = call.message.chat.id
            await call.message.answer("Оберіть тиждень", reply_markup=WeeksKeyboard('MainMenu', 'User', id_group))
    elif action == "MainMenu":
        await state.clear()
        if type_user == 'Admin':
            await call.message.answer("Ви повернулись у головне меню", reply_markup=AdminKeyboard(group_id))
        elif type_user == 'User':
            await call.message.answer("Ви повернулись у головне меню", reply_markup=StartKeyboard())

async def main():
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(form_router)

    await dp.start_polling(bot)

if __name__ == "__main__": #І запускаємо Ійого
    logging.basicConfig(level=logging.INFO, stream=sys.stdout) #Вивід в консоль

    asyncio.run(main())