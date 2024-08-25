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
from filters.chat_type import ChatTypeFilter
from keyboards.keyboard import (
    StartKeyboard,
    AdminKeyboard,
    DaysKeyboard,
    ConfirmationKeyboard,
    ChooseAdmin_kb,
    WeeksKeyboard,
    BackKb
)

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
TIME = config['TIME']

#path = "C:\\Users\\trepi\\Desktop\\Coding\\Timetable-sender\\pic\\picture.png"

###############################################################################



###############################################################################

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

###############################################################################

async def DownloadingPhotos(message: Message) -> tuple[str, str]:
    if message.photo:
        user_id = message.from_user.id
        file_id = message.photo[-1].file_id
        file_info = await message.bot.get_file(file_id)
        path = "C:\\Users\\trepi\\Desktop\\Coding\\Timetable-sender\\pic\\picture.png"
        await message.bot.download_file(file_info.file_path, destination=path)

        cursor.execute('''SELECT id FROM KNEU WHERE admin_group = ?''', (user_id,))
        result = cursor.fetchone()
        id_group = result[0] if result else None

        # Возвращаем путь и id_group
        return path, id_group
    return None, None

###############################################################################

@form_router.message(Command("admin"), ChatTypeFilter(chat_type = ['private']))
async def AdminMessage(message: Message) -> None:
    user_id = message.from_user.id
    cursor.execute("""SELECT admin_group FROM KNEU""")
    admin_users = cursor.fetchall()

    admin_user_ids = [user[0] for user in admin_users]

    if user_id not in admin_user_ids:
        await message.answer("Ви не є адміністратором жодної з груп. Якщо бажаєте стати адміністратором - додайте бота до своєї групи")
        return
    else:
        await message.answer("Оберіть функцію", reply_markup=AdminKeyboard())

@form_router.message(CommandStart(), ChatTypeFilter(chat_type = ["group", "supergroup"]))
async def StartMessage(message: Message, state: FSMContext) -> None:
    id_chat = message.chat.id
        
    '''cursor.execute("""SELECT admin_group FROM KNEU""")
    admin_users = cursor.fetchall()
    '''

    cursor.execute("""SELECT id FROM KNEU""")
    chats = cursor.fetchall()

    #admin_user_ids = [user[0] for user in admin_users]
    chats_ids = [chat[0] for chat in chats] 

    if id_chat not in chats_ids:
        await state.set_state(Form.GroupId)
        await message.answer("Вашої групи не має в базі. Бажаєте додати?", reply_markup=ConfirmationKeyboard())
        return
    else:
        await message.answer("Оберіть функцію", reply_markup=StartKeyboard())

@form_router.callback_query(lambda call: call.data == 'Confirm')
async def ConfirmAdd(call: CallbackQuery, state: FSMContext) -> None:
    await call.message.delete()
    id_chat = call.message.chat.id
    id_user = call.from_user.id

    await state.update_data(GroupId=id_chat, UserId=id_user)
    cursor.execute("""INSERT INTO KNEU (id) VALUES (?)""", (id_chat,))
    conn.commit()
    
    await state.update_data(GroupId=id_chat)
    await call.message.answer('''Вашу групу успішно додано до бази. Тепер оберіть людину, яка буде наповнювати мене актуальною інформацією про розклад занять, посилання на пари та пошти викладачів''', reply_markup=ChooseAdmin_kb())

@form_router.callback_query(lambda call: call.data == 'YesIAm')
async def ChooseAdmin(call: CallbackQuery, state: FSMContext) -> None:
    await call.message.delete()
    id_user = call.from_user.id
    data = await state.get_data()
    id_group = data.get('GroupId')

    cursor.execute('''UPDATE KNEU SET admin_group = ? WHERE id = ?''', (id_user, id_group,))
    conn.commit()
    await call.message.answer("Вітаю, адміністратора обрано. Починаємо налаштування бота")
    await call.bot.send_message(id_user, "Вітаю, тепер ви - адміністратор. Для налаштування бота введіть команду /admin")

###############################################################################

@form_router.callback_query(lambda call: call.data == 'AddTimetable')
async def SetTimetable(call: CallbackQuery, state: FSMContext) -> None:
    await call.message.delete()
    await call.message.answer("Оберіть тиждень", reply_markup=WeeksKeyboard('MainMenu', 'Admin'))

@form_router.callback_query(F.data.startswith('Top_Week') | F.data.startswith('Lower_Week'))
async def SetTimetable(call: CallbackQuery, state: FSMContext) -> None:
    parts = call.data.rsplit('_', 1)
    action, type_user = parts

    if action == 'Top_Week':
        if type_user == 'Admin':
            await call.message.delete()
            await call.message.answer("Ви обрали верхній тиждень", reply_markup=DaysKeyboard('Top', 'WeekSelection', 'Admin'))
        elif type_user == 'User':
            await call.message.delete()
            await call.message.answer("Ви обрали верхній тиждень. Оберіть день, розклад якого Вас цікавить", reply_markup=DaysKeyboard('Top', 'WeekSelection', 'User'))
    elif action == 'Lower_Week':
        if type_user == 'Admin':
            await call.message.delete()
            await call.message.answer("Ви обрали нижній тиждень", reply_markup=DaysKeyboard('Lower', 'WeekSelection', 'Admin'))
        elif type_user == 'User':
            await call.message.delete()
            await call.message.answer("Ви обрали нижній тиждень. Оберіть день, розклад якого Вас цікавить", reply_markup=DaysKeyboard('Lower', 'WeekSelection', 'User'))
    else:
        await call.message.answer("Невідомий вибір. Спробуйте ще раз.")

###############################################################################        

@form_router.callback_query(lambda call: call.data == 'PushLink')
async def SetLinks(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Form.Links)
    await call.message.delete()
    await call.message.answer("Окей. Відправте список предметів та посилань на їх пари. Будь ласка, слідуйте наступному формату:\n\nДисципліна1 - Посилання1\nДисципліна2 - Посилання2", reply_markup=BackKb('MainMenu','Admin'))

@form_router.message(Form.Links)
async def CheckLinks(message: Message, state: FSMContext) -> None:
    id_user = message.from_user.id
    cursor.execute("""SELECT id FROM KNEU WHERE admin_group = ?""", (id_user,))
    result = cursor.fetchone()
    id_group = result[0]

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
            await message.answer("Оберіть дію", reply_markup=AdminKeyboard())
        except Exception as e:
            await message.answer(f"Сталася помилка при збереженні даних: {str(e)}")
    else:
        await message.answer("Введені вами дані не відповідають вказаному формату. Будь ласка, спробуйте знову")

###############################################################################

@form_router.callback_query(lambda call: call.data == 'EnterEmails')
async def SetEmails(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Form.Emails)
    await call.message.delete()
    await call.message.answer("Окей. Відправте список дисциплін та пошти викладачів, які їх ведуть. Будь ласка, слідуйте наступному формату:\n\nДисципліна1 - Пошта1\nДисципліна2 - Пошта2", reply_markup=BackKb('MainMenu','Admin'))

@form_router.message(Form.Emails)
async def CheckEmails(message: Message, state: FSMContext) -> None:
    text_message = message.text
    is_valid, formatted_message = format_and_check_message(text_message)

    id_user = message.from_user.id
    cursor.execute("""SELECT id FROM KNEU WHERE admin_group = ?""", (id_user,))
    result = cursor.fetchone()
    id_group = result[0]

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
            await message.answer("Оберіть дію", reply_markup=AdminKeyboard())
        except Exception as e:
            await message.answer(f"Виникла помилка при збереженні данних: {str(e)}")
    else:
        await message.answer("Введені вами дані не відповідають формату 'Текст - Email'. Будь ласка, спробуйте знову.")
    

###############################################################################

@form_router.callback_query(F.data.startswith('Monday_'))
async def SetMondayTimetable(call: CallbackQuery, state: FSMContext) -> None:
    parts = call.data.split('_')

    _, action, type_user = parts

    await state.update_data(action=action)
    await state.update_data(type_user=type_user)
    await call.message.delete()

    if action == 'Lower':
        if type_user == 'Admin':
            await state.set_state(Form.MondayTimetable)
            await call.message.answer("Відправте розклад на понеділок нижнього тижня")
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
            await call.message.answer("Відправте розклад на понеділок верхнього тижня")
        elif type_user == 'User':
            id_group = call.message.chat.id
            cursor.execute("""SELECT timetable_monday_top FROM KNEU WHERE id = ?""", (id_group,))
            result = cursor.fetchone()
            timetable = result[0]

            if timetable == "Розкладу на понеділок верхнього тижня ще немає":
                await call.message.answer(f'<b>{timetable}</b>', reply_markup=BackKb('WeekSelection', 'User'))
            else:
                await call.message.answer(f'<a href="{timetable}"> </a><b>Розклад на понеділок верхнього тижня</b>', reply_markup=BackKb('WeekSelection', 'User'))

@form_router.callback_query(F.data.startswith('Tuesday_'))
async def SetTuesdayTimetable(call: CallbackQuery, state: FSMContext) -> None:
    parts = call.data.split('_')

    _, action, type_user = parts

    await state.update_data(action=action)
    await call.message.delete()

    if action == 'Lower':
        if type_user == 'Admin':
            await state.set_state(Form.TuesdayTimetable)
            await call.message.answer("Відправте розклад на вівторок нижнього тижня", reply_markup=BackKb('WeekSelection', 'User'))
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
            await call.message.answer("Відправте розклад на вівторок верхнього тижня")
        elif type_user == 'User':
            id_group = call.message.chat.id
            cursor.execute("""SELECT timetable_tuesday_top FROM KNEU WHERE id = ?""", (id_group,))
            result = cursor.fetchone()
            timetable = result[0]

            if timetable == "Розкладу на вівторок верхнього тижня ще немає":
                await call.message.answer(f'<b>{timetable}</b>', reply_markup=BackKb('WeekSelection', 'User'))
            else:
                await call.message.answer(f'<a href="{timetable}"> </a><b>Розклад на вівторок верхнього тижня</b>', reply_markup=BackKb('WeekSelection', 'User'))

@form_router.callback_query(F.data.startswith('Wednesday_'))
async def SetWednesdayTimetable(call: CallbackQuery, state: FSMContext) -> None:
    parts = call.data.split('_')

    _, action, type_user = parts

    await state.update_data(action=action)
    await call.message.delete()

    if action == 'Lower':
        if type_user == 'Admin':
            await state.set_state(Form.WednesdayTimetable)
            await call.message.answer("Відправте розклад на середу нижнього тижня")
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
            await call.message.answer("Відправте розклад на середу верхнього тижня")
        elif type_user == 'User':
            id_group = call.message.chat.id
            cursor.execute("""SELECT timetable_wednesday_top FROM KNEU WHERE id = ?""", (id_group,))
            result = cursor.fetchone()
            timetable = result[0]

            if timetable == "Розкладу на середу верхнього тижня ще немає":
                await call.message.answer(f'<b>{timetable}</b>', reply_markup=BackKb('WeekSelection', 'User'))
            else:
                await call.message.answer(f'<a href="{timetable}"> </a><b>Розклад на середу верхнього тижня</b>', reply_markup=BackKb('WeekSelection', 'User'))

@form_router.callback_query(F.data.startswith('Thursday_'))
async def SetThursdayTimetable(call: CallbackQuery, state: FSMContext) -> None:
    parts = call.data.split('_')

    _, action, type_user = parts

    await state.update_data(action=action)
    await call.message.delete()

    if action == 'Lower':
        if type_user == 'Admin':
            await state.set_state(Form.ThursdayTimetable)
            await call.message.answer("Відправте розклад на четвер нижнього тижня")
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
            await call.message.answer("Відправте розклад на четвер верхнього тижня")
        elif type_user == 'User':
            id_group = call.message.chat.id
            cursor.execute("""SELECT timetable_thursday_top FROM KNEU WHERE id = ?""", (id_group,))
            result = cursor.fetchone()
            timetable = result[0]

            if timetable == "Розкладу на четвер верхнього тижня ще немає":
                await call.message.answer(f'<b>{timetable}</b>', reply_markup=BackKb('WeekSelection', 'User'))
            else:
                await call.message.answer(f'<a href="{timetable}"> </a><b>Розклад на четвер верхнього тижня</b>', reply_markup=BackKb('WeekSelection', 'User'))

@form_router.callback_query(F.data.startswith('Friday_'))
async def SetFridayTimetable(call: CallbackQuery, state: FSMContext) -> None:
    parts = call.data.split('_')

    _, action, type_user = parts

    await state.update_data(action=action)
    await call.message.delete()

    if action == 'Lower':
        if type_user == 'Admin':
            await state.set_state(Form.FridayTimetable)
            await call.message.answer("Відправте розклад на п'ятницю нижнього тижня")
        elif type_user == 'User':
            id_group = call.message.chat.id
            cursor.execute("""SELECT timetable_Friday_lower FROM KNEU WHERE id = ?""", (id_group,))
            result = cursor.fetchone()
            timetable = result[0]

            if timetable == "Розкладу на п'ятницю нижнього тижня ще немає":
                await call.message.answer(f'<b>{timetable}</b>')
            else:
                await call.message.answer(f"<a href='{timetable}'> </a><b>Розклад на п'ятницю нижнього тижня</b>", reply_markup=BackKb('WeekSelection', 'User'))
    elif action == "Top":
        if type_user == 'Admin':
            await state.set_state(Form.FridayTimetable)
            await call.message.answer("Відправте розклад на п'ятницю верхнього тижня")
        elif type_user == 'User':
            id_group = call.message.chat.id
            cursor.execute("""SELECT timetable_friday_top FROM KNEU WHERE id = ?""", (id_group,))
            result = cursor.fetchone()
            timetable = result[0]

            if timetable == "Розкладу на п'ятницю верхнього тижня ще немає":
                await call.message.answer(f'<b>{timetable}</b>', reply_markup=BackKb('WeekSelection', 'User'))
            else:
                await call.message.answer(f"<a href='{timetable}'> </a><b>Розклад на п'ятницю верхнього тижня</b>", reply_markup=BackKb('WeekSelection', 'User'))

@form_router.callback_query(F.data.startswith('Back_'))
async def Back(call: CallbackQuery, state: FSMContext) -> None:
    parts = call.data.split('_')

    _, action, type_user = parts
    await call.message.delete()
    
    if action == "WeekSelection":
        if type_user == 'Admin':
            await call.message.answer("Оберіть тиждень", reply_markup=WeeksKeyboard('MainMenu', 'Admin'))
        elif type_user == 'User':
            await call.message.answer("Оберіть тиждень", reply_markup=WeeksKeyboard('MainMenu', 'User'))
    elif action == "MainMenu":
        await state.clear()
        if type_user == 'Admin':
            await call.message.answer("Ви повернулись у головне меню", reply_markup=AdminKeyboard())
        elif type_user == 'User':
            await call.message.answer("Ви повернулись у головне меню", reply_markup=StartKeyboard())

###############################################################################

@form_router.message(F.photo, Form.MondayTimetable)
async def SetMonday(message: Message, state: FSMContext) -> None:
    path, id_group = await DownloadingPhotos(message)
    
    data = await state.get_data()
    action = data.get('action')

    if path and id_group:
        url = telegraph_file_upload(path)
        await state.update_data(MondayTimetable=url)
        if action == "Lower":
            cursor.execute("""UPDATE KNEU SET timetable_monday_lower = ? WHERE id = ?""", (url, id_group))
            conn.commit()
            await message.answer(f"Розклад на понеділок нижнього тижня успішно збережено", reply_markup=DaysKeyboard('Lower', 'WeekSelection', 'Admin'))
        elif action == "Top":
            cursor.execute("""UPDATE KNEU SET timetable_monday_top = ? WHERE id = ?""", (url, id_group))
            conn.commit()
            await message.answer(f"Розклад на понеділок верхнього тижня успішно збережено", reply_markup=DaysKeyboard('Top','WeekSelection', 'Admin'))
        else:
            await message.answer(f"Виникла помилка")
    else:
        await message.answer("Адміністратор не знайдений у базі даних або файл не був завантажений.")

@form_router.message(F.photo, Form.TuesdayTimetable)
async def SetTuesday(message: Message, state: FSMContext) -> None:
    path, id_group = await DownloadingPhotos(message)
    
    data = await state.get_data()
    action = data.get('action')

    if path and id_group:
        url = telegraph_file_upload(path)
        await state.update_data(TuesdayTimetable=url)
        if action == "Lower":
            cursor.execute("""UPDATE KNEU SET timetable_tuesday_lower = ? WHERE id = ?""", (url, id_group))
            conn.commit()
            await message.answer(f"Розклад на вівторок нижнього тижня успішно збережено", reply_markup=DaysKeyboard('Lower','WeekSelection', 'Admin'))
        elif action == "Top":
            cursor.execute("""UPDATE KNEU SET timetable_tuesday_top = ? WHERE id = ?""", (url, id_group))
            conn.commit()
            await message.answer(f"Розклад на вівторок верхнього тижня успішно збережено", reply_markup=DaysKeyboard('Top','WeekSelection', 'Admin'))
        else:
            await message.answer(f"Виникла помилка")
    else:
        await message.answer("Адміністратор не знайдений у базі даних або файл не був завантажений.")

@form_router.message(F.photo, Form.WednesdayTimetable)
async def SetWednesday(message: Message, state: FSMContext) -> None:
    path, id_group = await DownloadingPhotos(message)
    
    data = await state.get_data()
    action = data.get('action')

    if path and id_group:
        url = telegraph_file_upload(path)
        await state.update_data(WednesdayTimetable=url)
        if action == "Lower":
            cursor.execute("""UPDATE KNEU SET timetable_wednesday_lower = ? WHERE id = ?""", (url, id_group))
            conn.commit()
            await message.answer(f"Розклад на середу нижнього тижня успішно збережено", reply_markup=DaysKeyboard('Lower','WeekSelection', 'Admin'))
        elif action == "Top":
            cursor.execute("""UPDATE KNEU SET timetable_wednesday_top = ? WHERE id = ?""", (url, id_group))
            conn.commit()
            await message.answer(f"Розклад на середу верхнього тижня успішно збережено", reply_markup=DaysKeyboard('Top','WeekSelection', 'Admin'))
        else:
            await message.answer(f"Виникла помилка")
    else:
        await message.answer("Адміністратор не знайдений у базі даних або файл не був завантажений.")

@form_router.message(F.photo, Form.ThursdayTimetable)
async def SetThursday(message: Message, state: FSMContext) -> None:
    path, id_group = await DownloadingPhotos(message)
    
    data = await state.get_data()
    action = data.get('action')

    if path and id_group:
        url = telegraph_file_upload(path)
        await state.update_data(ThursdayTimetable=url)
        if action == "Lower":
            cursor.execute("""UPDATE KNEU SET timetable_thursday_lower = ? WHERE id = ?""", (url, id_group))
            conn.commit()
            await message.answer(f"Розклад на четвер нижнього тижня успішно збережено", reply_markup=DaysKeyboard('Lower','WeekSelection', 'Admin'))
        elif action == "Top":
            cursor.execute("""UPDATE KNEU SET timetable_thursday_top = ? WHERE id = ?""", (url, id_group))
            conn.commit()
            await message.answer(f"Розклад на четвер верхнього тижня успішно збережено", reply_markup=DaysKeyboard('Top','WeekSelection', 'Admin'))
        else:
            await message.answer(f"Виникла помилка")
    else:
        await message.answer("Адміністратор не знайдений у базі даних або файл не був завантажений.")

@form_router.message(F.photo, Form.FridayTimetable)
async def SetFriday(message: Message, state: FSMContext) -> None:
    path, id_group = await DownloadingPhotos(message)
    
    data = await state.get_data()
    action = data.get('action')

    if path and id_group:
        url = telegraph_file_upload(path)
        await state.update_data(FridayTimetable=url)
        if action == "Lower":
            cursor.execute("""UPDATE KNEU SET timetable_friday_lower = ? WHERE id = ?""", (url, id_group))
            conn.commit()
            await message.answer(f"Розклад на четвер нижнього тижня успішно збережено", reply_markup=DaysKeyboard('Lower','WeekSelection', 'Admin'))
        elif action == "Top":
            cursor.execute("""UPDATE KNEU SET timetable_friday_top = ? WHERE id = ?""", (url, id_group))
            conn.commit()
            await message.answer(f"Розклад на четвер верхнього тижня успішно збережено", reply_markup=DaysKeyboard('Top','WeekSelection', 'Admin'))
        else:
            await message.answer(f"Виникла помилка")
    else:
        await message.answer("Адміністратор не знайдений у базі даних або файл не був завантажений.")

###############################################################################

@form_router.callback_query(lambda call: call.data == "DisplayTimetable")
async def GetTimetable(call: CallbackQuery, state: FSMContext) -> None:
    await call.message.delete()
    await call.message.answer("Оберіть тиждень", reply_markup=WeeksKeyboard('MainMenu', 'User'))

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

###############################################################################

async def main():
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(form_router)

    await dp.start_polling(bot)

if __name__ == "__main__": #І запускаємо Ійого
    logging.basicConfig(level=logging.INFO, stream=sys.stdout) #Вивід в консоль

    asyncio.run(main())