import asyncio #Імпорти
import logging
import sys
from typing import Any, Dict
import json
import sqlite3
import requests
import re
import os

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from keyboards.keyboard import(
    StartKeyboard,
    AdminKeyboard,
    DaysKeyboard,
    WeeksKeyboard,
    ConfirmationKeyboard,
    ChooseAdmin_kb,
    BackKb,
    ChangeAdminConfirmation,
    HelpKb
)

from filters.chat_type import ChatTypeFilter

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

form_router = Router() #Роутер

conn = sqlite3.connect("data.db")#Database
cursor = conn.cursor()

class Form(StatesGroup): #Клас зі стейтами
    MondayTimetable = State()
    TuesdayTimetable = State()
    WednesdayTimetable = State()
    ThursdayTimetable = State()
    FridayTimetable = State()
    SaturdayTimetable = State()

    GroupId = State()
    Links = State()
    Emails = State()

    ChangeAdmin = State()

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

async def DownloadingPhotos(message: Message) -> tuple[str, str]:
    if message.photo:
        file_id = message.photo[-1].file_id
        file_info = await message.bot.get_file(file_id)

        dir_path = os.path.join(os.getcwd(), 'pic')
        path = os.path.join(dir_path, 'picture.png')

        os.makedirs(dir_path, exist_ok=True)

        await message.bot.download_file(file_info.file_path, destination=path)

        return path
    return None

async def get_admin_groups(user_id):
    cursor.execute('''SELECT id, chat_name FROM KNEU WHERE admin_group = ?''', (user_id,))
    groups = cursor.fetchall()
    return groups

@form_router.message(Command("configure"), ChatTypeFilter(chat_type=['private']))
async def AdminMessage(message: Message) -> None:
    try:
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
    except Exception as e:
        await message.answer(f"Виникла помилка: <code>{e}</code>. <b>ID: 1</b>. Задля її усунення зверніться будь ласка до @Zakhiel")

@form_router.callback_query(lambda call: call.data.startswith("configure_group_"))
async def configure_selected_group(call: CallbackQuery, state: FSMContext):
    try:
        await call.message.delete()
        group_id = int(call.data.split("_")[-1])
        cursor.execute("""SELECT chat_name FROM KNEU WHERE id = ?""", (group_id,))
        res = cursor.fetchone()
        chat_name = res[0]

        await state.update_data(selected_group=group_id)
        
        await call.message.answer(f"Ви обрали групу <b>{chat_name}</b>. Тепер ви можете виконувати налаштування.", reply_markup=AdminKeyboard(group_id))
    except Exception as e:
        await call.message.answer(f"Виникла помилка: <code>{e}</code>. <b>ID: 2</b>. Задля її усунення зверніться будь ласка до @Zakhiel")

@form_router.message(Command("configure"), ChatTypeFilter(chat_type = ["group", "supergroup"]))
async def AdminMessage(message: Message) -> None:
    try:
        await message.answer("❌ <b>Налаштування боту доступне лише в приватних повідомленнях.</b>\n\nБудь ласка, перейдіть в приватні поведомлення з ботом та повторіть цю команду")
    except Exception as e:
        await message.answer(f"Виникла помилка: <code>{e}</code>. <b>ID: 3</b>. Задля її усунення зверніться будь ласка до @Zakhiel")

@form_router.message(F.new_chat_title)
async def ChangeChatNameBD(message: Message):
    try:
        id_chat = message.chat.id
        chat_name = message.chat.full_name

        cursor.execute('''UPDATE KNEU SET chat_name = ? WHERE id = ?''', (chat_name, id_chat,))
        conn.commit()
    except Exception as e:
        await message.answer(f"Виникла помилка: <code>{e}</code>. <b>ID: 3.5</b>. Задля її усунення зверніться будь ласка до @Zakhiel")

@form_router.message(CommandStart(), ChatTypeFilter(chat_type = ["group", "supergroup"]))
async def StartMessage(message: Message, state: FSMContext) -> None:
    try:
        id_chat = message.chat.id

        cursor.execute("""SELECT id FROM KNEU""")
        chats = cursor.fetchall()

        chats_ids = [chat[0] for chat in chats] 

        if id_chat not in chats_ids:
            await message.answer("❌ Вашої групи не має в базі. <b>Бажаєте додати?</b>", reply_markup=ConfirmationKeyboard())
            return
        else:
            await message.answer("Оберіть функцію", reply_markup=StartKeyboard())
            
    except Exception as e:
        await message.answer(f"Виникла помилка: <code>{e}</code>. <b>ID: 4</b>. Задля її усунення зверніться будь ласка до @Zakhiel")

@form_router.message(CommandStart(), ChatTypeFilter(chat_type = ["private"]))
async def CancelStart(message: Message):
    try:
        await message.answer("<b>Вітаю!</b>👋\n\nДля того, щоб мати змогу працювати зі мною - додайте мене до Вашої групи та відправте ще раз команду /start в груповому чаті")
    except Exception as e:
        await message.answer(f"Виникла помилка: <code>{e}</code>. <b>ID: 5</b>. Задля її усунення зверніться будь ласка до @Zakhiel")

@form_router.callback_query(lambda call: call.data == 'Confirm')
async def ConfirmAdd(call: CallbackQuery, state: FSMContext) -> None:
    try:
        await call.message.delete()
        id_chat = call.message.chat.id
        id_user = call.from_user.id
        name_chat = call.message.chat.full_name

        await state.update_data(GroupId=id_chat, UserId=id_user)
        cursor.execute("""INSERT INTO KNEU (id, chat_name) VALUES (?,?)""", (id_chat, name_chat,))
        conn.commit()
        
        await state.update_data(GroupId=id_chat)
        await call.message.answer('''✅ <b>Вашу групу успішно додано до бази.</b>\n\nТепер оберіть людину, яка буде наповнювати мене актуальною інформацією про розклад занять, посилання на пари та пошти викладачів''', reply_markup=ChooseAdmin_kb())
    except Exception as e:
        await call.message.answer(f"Виникла помилка: <code>{e}</code>. <b>ID: 6</b>. Задля її усунення зверніться будь ласка до @Zakhiel")       

@form_router.callback_query(lambda call: call.data == 'Cancel')
async def decline_add(call: CallbackQuery) -> None:
    try: 
        chat_id = call.message.chat.id
        await call.message.delete()
        await call.message.answer("""<b>Вас зрозумів 🫡</b>\n\nЯк знадоблюся - Ви завжди можете додати мене назад до чату""")
        await call.bot.leave_chat(chat_id)
    except Exception as e:
        await call.message.answer(f"Виникла помилка: <code>{e}</code>. <b>ID: 7</b>. Задля її усунення зверніться будь ласка до @Zakhiel")

@form_router.callback_query(lambda call: call.data == 'YesIAm')
async def ChooseAdmin(call: CallbackQuery) -> None:
    try:
        await call.message.delete()
        id_user = call.from_user.id
        admin_user_name = call.from_user.full_name
        id_group = call.message.chat.id

        cursor.execute('''UPDATE KNEU SET admin_group = ? WHERE id = ?''', (id_user, id_group,))
        conn.commit()

        await call.message.answer(f"Вітаю, адміністратора обрано (<b>{admin_user_name}</b>). Перейдіть до мене в особисті повідомлення та відправте команду /configure")
        await call.bot.send_message(id_user, "Вітаю, тепер ви - адміністратор. Для налаштування бота введіть команду /configure")
    except Exception as e:
        await call.message.answer(f"Виникла помилка: <code>{e}</code>. <b>ID: 8</b>. Задля її усунення зверніться будь ласка до @Zakhiel")

@form_router.callback_query(F.data.startswith('AddTimetable_'))
async def SetTimetable(call: CallbackQuery, state: FSMContext) -> None:
    try:
        parts = call.data.split('_')
        _, group_id = parts

        await call.message.delete()
        await call.message.answer("Оберіть тиждень", reply_markup=WeeksKeyboard('MainMenu', 'Admin', group_id))
    except Exception as e:
        await call.message.answer(f"Виникла помилка: <code>{e}</code>. <b>ID: 9</b>. Задля її усунення зверніться будь ласка до @Zakhiel")

@form_router.callback_query(F.data.startswith('Top_Week') | F.data.startswith('Lower_Week'))
async def SetTimetable(call: CallbackQuery, state: FSMContext) -> None:
    try:
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
    except Exception as e:
        await call.message.answer(f"Виникла помилка: <code>{e}</code>. <b>ID: 10</b>. Задля її усунення зверніться будь ласка до @Zakhiel")    

@form_router.callback_query(F.data.startswith('Monday_'))
async def SetMondayTimetable(call: CallbackQuery, state: FSMContext) -> None:
    try:
        parts = call.data.split('_')

        _, action, type_user, id_group = parts

        await state.update_data(action=action)
        await state.update_data(type_user=type_user)
        await state.update_data(id_group=id_group)
        await call.message.delete()

        if action == 'Lower':
            if type_user == 'Admin':
                await state.set_state(Form.MondayTimetable)
                await call.message.answer("Відправте розклад на понеділок нижнього тижня", reply_markup=BackKb('WeekSelection', 'Admin', id_group))
            elif type_user == 'User':
                id_group = call.message.chat.id
                cursor.execute("""SELECT timetable_monday_lower FROM KNEU WHERE id = ?""", (id_group,))
                result = cursor.fetchone()
                timetable = result[0]

                if timetable == "Розкладу на понеділок нижнього тижня ще немає":
                    await call.message.answer(f'<b>{timetable}</b>', reply_markup=BackKb('WeekSelection', 'User', id_group))
                else:
                    await call.message.answer(f'<a href="{timetable}"> </a><b>Розклад на понеділок нижнього тижня</b>', reply_markup=BackKb('WeekSelection', 'User', id_group))
        elif action == "Top":
            if type_user == 'Admin':
                await state.set_state(Form.MondayTimetable)
                await call.message.answer("Відправте розклад на понеділок верхнього тижня", reply_markup=BackKb('WeekSelection', 'Admin', id_group))
            elif type_user == 'User':
                id_group = call.message.chat.id
                cursor.execute("""SELECT timetable_monday_top FROM KNEU WHERE id = ?""", (id_group,))
                result = cursor.fetchone()
                timetable = result[0]

                if timetable == "Розкладу на понеділок верхнього тижня ще немає":
                    await call.message.answer(f'<b>{timetable}</b>', reply_markup=BackKb('WeekSelection', 'User', id_group))
                else:
                    await call.message.answer(f'<a href="{timetable}"> </a><b>Розклад на понеділок верхнього тижня</b>', reply_markup=BackKb('WeekSelection', 'User', id_group))
    except Exception as e:
        await call.message.answer(f"Виникла помилка: <code>{e}</code>. <b>ID: 11</b>. Задля її усунення зверніться будь ласка до @Zakhiel")    

@form_router.message(Form.MondayTimetable)
async def SetMonday(message: Message, state: FSMContext) -> None:
    try:
        data = await state.get_data()
        action = data.get('action')
        id_group = data.get('id_group')
    
        if not message.photo:
            await message.answer("Будь ласка, надішліть розклад як фото", reply_markup=BackKb('WeekSelection', 'Admin', id_group))
            return

        path = await DownloadingPhotos(message)

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
    except Exception as e:
        await message.answer(f"Виникла помилка: <code>{e}</code>. <b>ID: 12</b>. Задля її усунення зверніться будь ласка до @Zakhiel")    

@form_router.callback_query(F.data.startswith('Tuesday_'))
async def SetTuesdayTimetable(call: CallbackQuery, state: FSMContext) -> None:
    try:
        parts = call.data.split('_')

        _, action, type_user, id_group = parts

        await state.update_data(action=action)
        await state.update_data(type_user=type_user)
        await state.update_data(id_group=id_group)
        await call.message.delete()

        if action == 'Lower':
            if type_user == 'Admin':
                await state.set_state(Form.TuesdayTimetable)
                await call.message.answer("Відправте розклад на вівторок нижнього тижня", reply_markup=BackKb('WeekSelection', 'Admin', id_group))
            elif type_user == 'User':
                id_group = call.message.chat.id
                cursor.execute("""SELECT timetable_tuesday_lower FROM KNEU WHERE id = ?""", (id_group,))
                result = cursor.fetchone()
                timetable = result[0]

                if timetable == "Розкладу на вівторок нижнього тижня ще немає":
                    await call.message.answer(f'<b>{timetable}</b>', reply_markup=BackKb('WeekSelection', 'User', id_group))
                else:
                    await call.message.answer(f'<a href="{timetable}"> </a><b>Розклад на вівторок нижнього тижня</b>', reply_markup=BackKb('WeekSelection', 'User', id_group))
        elif action == "Top":
            if type_user == 'Admin':
                await state.set_state(Form.TuesdayTimetable)
                await call.message.answer("Відправте розклад на вівторок верхнього тижня", reply_markup=BackKb('WeekSelection', 'Admin', id_group))
            elif type_user == 'User':
                id_group = call.message.chat.id
                cursor.execute("""SELECT timetable_tuesday_top FROM KNEU WHERE id = ?""", (id_group,))
                result = cursor.fetchone()
                timetable = result[0]

                if timetable == "Розкладу на вівторок верхнього тижня ще немає":
                    await call.message.answer(f'<b>{timetable}</b>', reply_markup=BackKb('WeekSelection', 'User', id_group))
                else:
                    await call.message.answer(f'<a href="{timetable}"> </a><b>Розклад на вівторок верхнього тижня</b>', reply_markup=BackKb('WeekSelection', 'User', id_group))
    except Exception as e:
        await call.message.answer(f"Виникла помилка: <code>{e}</code>. <b>ID: 13</b>. Задля її усунення зверніться будь ласка до @Zakhiel")    

@form_router.message(Form.TuesdayTimetable)
async def SetTuesday(message: Message, state: FSMContext) -> None:
    try:
        data = await state.get_data()
        action = data.get('action')
        id_group = data.get('id_group')

        if not message.photo:
            await message.answer("Будь ласка, надішліть розклад як фото", reply_markup=BackKb('WeekSelection', 'Admin', id_group))
            return
        path = await DownloadingPhotos(message)
        
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
    except Exception as e:
        await message.answer(f"Виникла помилка: <code>{e}</code>. <b>ID: 14</b>. Задля її усунення зверніться будь ласка до @Zakhiel")    

@form_router.callback_query(F.data.startswith('Wednesday_'))
async def SetWednesdayTimetable(call: CallbackQuery, state: FSMContext) -> None:
    try:
        parts = call.data.split('_')

        _, action, type_user, id_group = parts

        await state.update_data(action=action)
        await state.update_data(type_user=type_user)
        await state.update_data(id_group=id_group)
        await call.message.delete()

        if action == 'Lower':
            if type_user == 'Admin':
                await state.set_state(Form.WednesdayTimetable)
                await call.message.answer("Відправте розклад на середу нижнього тижня", reply_markup=BackKb('WeekSelection', 'Admin', id_group))
            elif type_user == 'User':
                id_group = call.message.chat.id
                cursor.execute("""SELECT timetable_wednesday_lower FROM KNEU WHERE id = ?""", (id_group,))
                result = cursor.fetchone()
                timetable = result[0]

                if timetable == "Розкладу на середу нижнього тижня ще немає":
                    await call.message.answer(f'<b>{timetable}</b>', reply_markup=BackKb('WeekSelection', 'User', id_group))
                else:
                    await call.message.answer(f'<a href="{timetable}"> </a><b>Розклад на середу нижнього тижня</b>', reply_markup=BackKb('WeekSelection', 'User', id_group))
        elif action == "Top":
            if type_user == 'Admin':
                await state.set_state(Form.WednesdayTimetable)
                await call.message.answer("Відправте розклад на середу верхнього тижня", reply_markup=BackKb('WeekSelection', 'Admin', id_group))
            elif type_user == 'User':
                id_group = call.message.chat.id
                cursor.execute("""SELECT timetable_wednesday_top FROM KNEU WHERE id = ?""", (id_group,))
                result = cursor.fetchone()
                timetable = result[0]

                if timetable == "Розкладу на середу верхнього тижня ще немає":
                    await call.message.answer(f'<b>{timetable}</b>', reply_markup=BackKb('WeekSelection', 'User', id_group))
                else:
                    await call.message.answer(f'<a href="{timetable}"> </a><b>Розклад на середу верхнього тижня</b>', reply_markup=BackKb('WeekSelection', 'User', id_group))
    except Exception as e:
        await call.message.answer(f"Виникла помилка: <code>{e}</code>. <b>ID: 15</b>. Задля її усунення зверніться будь ласка до @Zakhiel")    

@form_router.message(Form.WednesdayTimetable)
async def SetWednesday(message: Message, state: FSMContext) -> None:
    try:
        data = await state.get_data()
        action = data.get('action')
        id_group = data.get('id_group')

        if not message.photo:
            await message.answer("Будь ласка, надішліть розклад як фото", reply_markup=BackKb('WeekSelection', 'Admin', id_group))
            return
        path = await DownloadingPhotos(message)

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
    except Exception as e:
        await message.answer(f"Виникла помилка: <code>{e}</code>. <b>ID: 16</b>. Задля її усунення зверніться будь ласка до @Zakhiel")    

@form_router.callback_query(F.data.startswith('Thursday_'))
async def SetThursdayTimetable(call: CallbackQuery, state: FSMContext) -> None:
    try:
        parts = call.data.split('_')

        _, action, type_user, id_group = parts

        await state.update_data(action=action)
        await state.update_data(type_user=type_user)
        await state.update_data(id_group=id_group)
        await call.message.delete()

        if action == 'Lower':
            if type_user == 'Admin':
                await state.set_state(Form.ThursdayTimetable)
                await call.message.answer("Відправте розклад на четвер нижнього тижня", reply_markup=BackKb('WeekSelection', 'Admin', id_group))
            elif type_user == 'User':
                id_group = call.message.chat.id
                cursor.execute("""SELECT timetable_thursday_lower FROM KNEU WHERE id = ?""", (id_group,))
                result = cursor.fetchone()
                timetable = result[0]

                if timetable == "Розкладу на четвер нижнього тижня ще немає":
                    await call.message.answer(f'<b>{timetable}</b>', reply_markup=BackKb('WeekSelection', 'User', id_group))
                else:
                    await call.message.answer(f'<a href="{timetable}"> </a><b>Розклад на четвер нижнього тижня</b>', reply_markup=BackKb('WeekSelection', 'User', id_group))
        elif action == "Top":
            if type_user == 'Admin':
                await state.set_state(Form.ThursdayTimetable)
                await call.message.answer("Відправте розклад на четвер верхнього тижня", reply_markup=BackKb('WeekSelection', 'Admin', id_group))
            elif type_user == 'User':
                id_group = call.message.chat.id
                cursor.execute("""SELECT timetable_thursday_top FROM KNEU WHERE id = ?""", (id_group,))
                result = cursor.fetchone()
                timetable = result[0]

                if timetable == "Розкладу на четвер верхнього тижня ще немає":
                    await call.message.answer(f'<b>{timetable}</b>', reply_markup=BackKb('WeekSelection', 'User', id_group))
                else:
                    await call.message.answer(f'<a href="{timetable}"> </a><b>Розклад на четвер верхнього тижня</b>', reply_markup=BackKb('WeekSelection', 'User', id_group))
    except Exception as e:
        await call.message.answer(f"Виникла помилка: <code>{e}</code>. <b>ID: 17</b>. Задля її усунення зверніться будь ласка до @Zakhiel")    

@form_router.message(Form.ThursdayTimetable)
async def SetThursday(message: Message, state: FSMContext) -> None:
    try:
        data = await state.get_data()
        action = data.get('action')
        id_group = data.get('id_group')

        if not message.photo:
            await message.answer("Будь ласка, надішліть розклад як фото", reply_markup=BackKb('WeekSelection', 'Admin', id_group))
            return
        path = await DownloadingPhotos(message)

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
    except Exception as e:
        await message.answer(f"Виникла помилка: <code>{e}</code>. <b>ID: 18</b>. Задля її усунення зверніться будь ласка до @Zakhiel")    

@form_router.callback_query(F.data.startswith('Friday_'))
async def SetFridayTimetable(call: CallbackQuery, state: FSMContext) -> None:
    try:
        parts = call.data.split('_')

        _, action, type_user, id_group = parts

        await state.update_data(action=action)
        await state.update_data(type_user=type_user)
        await state.update_data(id_group=id_group)
        await call.message.delete()

        if action == 'Lower':
            if type_user == 'Admin':
                await state.set_state(Form.FridayTimetable)
                await call.message.answer("Відправте розклад на п'ятницю нижнього тижня", reply_markup=BackKb('WeekSelection', 'Admin', id_group))
            elif type_user == 'User':
                id_group = call.message.chat.id
                cursor.execute("""SELECT timetable_friday_lower FROM KNEU WHERE id = ?""", (id_group,))
                result = cursor.fetchone()
                timetable = result[0]

                if timetable == "Розкладу на п'ятницю нижнього тижня ще немає":
                    await call.message.answer(f'<b>{timetable}</b>', reply_markup=BackKb('WeekSelection', 'User', id_group))
                else:
                    await call.message.answer(f"<a href='{timetable}'> </a><b>Розклад на п'ятницю нижнього тижня</b>", reply_markup=BackKb('WeekSelection', 'User', id_group))
        elif action == "Top":
            if type_user == 'Admin':
                await state.set_state(Form.FridayTimetable)
                await call.message.answer("Відправте розклад на п'ятницю верхнього тижня", reply_markup=BackKb('WeekSelection', 'Admin', id_group))
            elif type_user == 'User':
                id_group = call.message.chat.id
                cursor.execute("""SELECT timetable_friday_top FROM KNEU WHERE id = ?""", (id_group,))
                result = cursor.fetchone()
                timetable = result[0]

                if timetable == "Розкладу на п'ятницю верхнього тижня ще немає":
                    await call.message.answer(f'<b>{timetable}</b>', reply_markup=BackKb('WeekSelection', 'User', id_group))
                else:
                    await call.message.answer(f"<a href='{timetable}'> </a><b>Розклад на п'ятницю верхнього тижня</b>", reply_markup=BackKb('WeekSelection', 'User', id_group))
    except Exception as e:
        await call.message.answer(f"Виникла помилка: <code>{e}</code>. <b>ID: 19</b>. Задля її усунення зверніться будь ласка до @Zakhiel")    

@form_router.message(Form.FridayTimetable)
async def SetFriday(message: Message, state: FSMContext) -> None:
    try:
        data = await state.get_data()
        action = data.get('action')
        id_group = data.get('id_group')

        if not message.photo:
            await message.answer("Будь ласка, надішліть розклад як фотографію", reply_markup=BackKb('WeekSelection', 'Admin', id_group))
            return
        path = await DownloadingPhotos(message)

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
    except Exception as e:
        await message.answer(f"Виникла помилка: <code>{e}</code>. <b>ID: 20</b>. Задля її усунення зверніться будь ласка до @Zakhiel")    

@form_router.callback_query(F.data.startswith('Saturday_'))
async def SetSaturdayTimetable(call: CallbackQuery, state: FSMContext) -> None:
    try:
        parts = call.data.split('_')

        _, action, type_user, id_group = parts

        await state.update_data(action=action)
        await state.update_data(type_user=type_user)
        await state.update_data(id_group=id_group)
        await call.message.delete()

        if action == 'Lower':
            if type_user == 'Admin':
                await state.set_state(Form.SaturdayTimetable)
                await call.message.answer("Відправте розклад на суботу нижнього тижня", reply_markup=BackKb('WeekSelection', 'Admin', id_group))
            elif type_user == 'User':
                id_group = call.message.chat.id
                cursor.execute("""SELECT timetable_saturday_lower FROM KNEU WHERE id = ?""", (id_group,))
                result = cursor.fetchone()
                timetable = result[0]

                if timetable == "Розкладу на суботу нижнього тижня ще немає":
                    await call.message.answer(f'<b>{timetable}</b>', reply_markup=BackKb('WeekSelection', 'User', id_group))
                else:
                    await call.message.answer(f'<a href="{timetable}"> </a><b>Розклад на суботу нижнього тижня</b>', reply_markup=BackKb('WeekSelection', 'User', id_group))
        elif action == "Top":
            if type_user == 'Admin':
                await state.set_state(Form.SaturdayTimetable)
                await call.message.answer("Відправте розклад на суботу верхнього тижня", reply_markup=BackKb('WeekSelection', 'Admin', id_group))
            elif type_user == 'User':
                id_group = call.message.chat.id
                cursor.execute("""SELECT timetable_saturday_top FROM KNEU WHERE id = ?""", (id_group,))
                result = cursor.fetchone()
                timetable = result[0]

                if timetable == "Розкладу на суботу верхнього тижня ще немає":
                    await call.message.answer(f'<b>{timetable}</b>', reply_markup=BackKb('WeekSelection', 'User', id_group))
                else:
                    await call.message.answer(f'<a href="{timetable}"> </a><b>Розклад на суботу верхнього тижня</b>', reply_markup=BackKb('WeekSelection', 'User', id_group))
    except Exception as e:
        await call.message.answer(f"Виникла помилка: <code>{e}</code>. <b>ID: saturday</b>. Задля її усунення зверніться будь ласка до @Zakhiel")    

@form_router.message(Form.SaturdayTimetable)
async def Setsaturday(message: Message, state: FSMContext) -> None:
    try:
        data = await state.get_data()
        action = data.get('action')
        id_group = data.get('id_group')
        
        if not message.photo:
            await message.answer("Будь ласка, надішліть розклад як фото", reply_markup=BackKb('WeekSelection', 'Admin', id_group))
            return
        
        path = await DownloadingPhotos(message)

        if path and id_group:
            url = telegraph_file_upload(path)
            await state.update_data(SaturdayTimetable=url)
            if action == "Lower":
                cursor.execute("""UPDATE KNEU SET timetable_saturday_lower = ? WHERE id = ?""", (url, id_group))
                conn.commit()
                await message.answer(f"Розклад на суботу нижнього тижня успішно збережено", reply_markup=DaysKeyboard('Lower', 'WeekSelection', 'Admin', id_group))
            elif action == "Top":
                cursor.execute("""UPDATE KNEU SET timetable_saturday_top = ? WHERE id = ?""", (url, id_group))
                conn.commit()
                await message.answer(f"Розклад на суботу верхнього тижня успішно збережено", reply_markup=DaysKeyboard('Top','WeekSelection', 'Admin', id_group))
            else:
                await message.answer(f"Виникла помилка")
        else:
            await message.answer("Адміністратор не знайдений у базі даних або файл не був завантажений.")
    except Exception as e:
        await message.answer(f"Виникла помилка: <code>{e}</code>. <b>ID: saturday_load</b>. Задля її усунення зверніться будь ласка до @Zakhiel")    

@form_router.callback_query(F.data.startswith('PushLink_'))
async def SetLinks(call: CallbackQuery, state: FSMContext) -> None:
    try:
        parts = call.data.split('_')
        _, id_group = parts

        await state.set_state(Form.Links)
        await state.update_data(id_group=id_group)
        await call.message.delete()
        await call.message.answer("Окей. Відправте список предметів та посилань на їх пари. Будь ласка, слідуйте наступному формату:\n\nДисципліна1 - Посилання1\nДисципліна2 - Посилання2", reply_markup=BackKb('MainMenu','Admin', id_group))
    except Exception as e:
        await call.message.answer(f"Виникла помилка: <code>{e}</code>. <b>ID: 21</b>. Задля її усунення зверніться будь ласка до @Zakhiel")    

@form_router.message(Form.Links)
async def CheckLinks(message: Message, state: FSMContext) -> None:
    try:
        data = await state.get_data()
        id_group = data.get("id_group")

        if not message.text:
            await message.answer("Будь ласка, надішліть список предметів та посилань на їх пари в форматі:\n\nДисципліна1 - Посилання1\nДисципліна2 - Посилання2", reply_markup=BackKb('MainMenu','Admin', id_group))
            return

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
            await message.answer("Введені вами дані не відповідають вказаному формату. Будь ласка, спробуйте знову", reply_markup=BackKb('MainMenu','Admin', id_group))
    except Exception as e:
        await message.answer(f"Виникла помилка: <code>{e}</code>. <b>ID: 22</b>. Задля її усунення зверніться будь ласка до @Zakhiel")    

@form_router.callback_query(F.data.startswith('EnterEmails_'))
async def SetEmails(call: CallbackQuery, state: FSMContext) -> None:
    try:
        parts = call.data.split('_')
        _, id_group = parts
        
        await state.set_state(Form.Emails)
        await state.update_data(id_group=id_group)
        await call.message.delete()
        await call.message.answer("Окей. Відправте список дисциплін та пошти викладачів, які їх ведуть. Будь ласка, слідуйте наступному формату:\n\nДисципліна1 - Пошта1\nДисципліна2 - Пошта2", reply_markup=BackKb('MainMenu','Admin', id_group))
    except Exception as e:
        await call.message.answer(f"Виникла помилка: <code>{e}</code>. <b>ID: 23</b>. Задля її усунення зверніться будь ласка до @Zakhiel")    

@form_router.message(Form.Emails)
async def CheckEmails(message: Message, state: FSMContext) -> None:
    try:
        data = await state.get_data()
        id_group = data.get("id_group")

        if not message.text:
            await message.answer("Будь ласка, надішліть список предметів та посилань на їх пари в форматі:\n\nДисципліна1 - Пошта1\nДисципліна2 - Пошта2", reply_markup=BackKb('MainMenu','Admin', id_group))
            return
        text_message = message.text

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
            await message.answer("Введені вами дані не відповідають формату 'Текст - Email'. Будь ласка, спробуйте знову.", reply_markup=BackKb('MainMenu','Admin', id_group))
    except Exception as e:
        await message.answer(f"Виникла помилка: <code>{e}</code>. <b>ID: 24</b>. Задля її усунення зверніться будь ласка до @Zakhiel")    

@form_router.callback_query(lambda call: call.data == "DisplayTimetable")
async def GetTimetable(call: CallbackQuery) -> None:
    try: 
        id_group = call.message.chat.id
        await call.message.delete()
        await call.message.answer("Оберіть тиждень", reply_markup=WeeksKeyboard('MainMenu', 'User', id_group))
    except Exception as e:
        await call.message.answer(f"Виникла помилка: <code>{e}</code>. <b>ID: 25</b>. Задля її усунення зверніться будь ласка до @Zakhiel")    

@form_router.callback_query(lambda call: call.data == "GetLink")
async def GetLinks(call: CallbackQuery) -> None:
    try:
        id_group = call.message.chat.id
        await call.message.delete()
        
        cursor.execute("SELECT lessons FROM KNEU WHERE id = ?", (id_group,))
        result = cursor.fetchone()
        lessons = result[0]

        is_valid, formatted_message = format_message_with_bold(lessons)

        await call.message.answer(f"<b>Посилання на пари:</b>\n\n{formatted_message}", reply_markup=BackKb('MainMenu', 'User', id_group))
    except Exception as e:
        await call.message.answer(f"Виникла помилка: <code>{e}</code>. <b>ID: 26</b>. Задля її усунення зверніться будь ласка до @Zakhiel")    

@form_router.callback_query(lambda call: call.data == "Emails")
async def GetEmails(call: CallbackQuery, state: FSMContext) -> None:
    try:
        id_group = call.message.chat.id
        await call.message.delete()
        
        cursor.execute("SELECT emails FROM KNEU WHERE id = ?", (id_group,))
        result = cursor.fetchone()
        emails = result[0]

        is_valid, formatted_message = format_and_check_message(emails)

        await call.message.answer(f"<b>Пошти викладачів:</b>\n\n{formatted_message}", reply_markup=BackKb('MainMenu', 'User', id_group))
    except Exception as e:
        await call.message.answer(f"Виникла помилка: <code>{e}</code>. <b>ID: 27</b>. Задля її усунення зверніться будь ласка до @Zakhiel")    
        
@form_router.callback_query(F.data.startswith('Back_'))
async def Back(call: CallbackQuery, state: FSMContext) -> None:
    try:
        parts = call.data.split('_')

        _, action, type_user, group_id = parts
        await call.message.delete()

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
    except Exception as e:
        await call.message.answer(f"Виникла помилка: <code>{e}</code>. <b>ID: 28</b>. Задля її усунення зверніться будь ласка до @Zakhiel")        

@form_router.callback_query(F.data.startswith("ChangeAdmin_"))
async def ChangeAdmin(call: CallbackQuery, state: FSMContext):
    try:
        parts = call.data.split('_')
        _, group_id = parts

        await call.message.delete()
        await state.update_data(group_id=group_id)

        await state.set_state(Form.ChangeAdmin)
        await call.message.answer("Перешліть повідомлення від користувача, якого Ви хочете назначити адміністратором", reply_markup=BackKb('MainMenu', 'Admin', group_id))
    except Exception as e:
        await call.message.answer(f"Виникла помилка: <code>{e}</code>. <b>ID: 29</b>. Задля її усунення зверніться будь ласка до @Zakhiel")        


@form_router.message(Form.ChangeAdmin)
async def ConfirmChangeAdmin(message: Message, state: FSMContext):
    try:
        if not message.forward_from:
            await message.answer("Це повідомлення не є форвардом від користувача. Будь ласка, перешліть повідомлення від користувача")
            return

        if message.forward_from.is_bot or message.forward_from.id <= 0:
            await message.answer("Це повідомлення переслане не від користувача. Будь ласка, перешліть повідомлення від користувача")
            return
        
        id_user = message.forward_from.id
        name_user = message.forward_from.full_name
        data = await state.get_data()
        id_group = data.get("group_id")
        
        await state.update_data(id_new_admin=id_user)

        await message.answer(f"Ви точно впевнені, що бажаєте передати права адміністратора користувачу <b>{name_user}</b>?", 
                            reply_markup=ChangeAdminConfirmation(id_group))
    except Exception as e:
        await message.answer(f"Виникла помилка: <code>{e}</code>. <b>ID: 30</b>. Задля її усунення зверніться будь ласка до @Zakhiel")        

@form_router.callback_query(F.data.startswith("ConfirmChange_") | F.data.startswith("CancelChange_"))
async def GoodChangeAdmin(call: CallbackQuery, state: FSMContext):
    try:
        parts = call.data.split('_')
        _, id_group = parts
        
        await call.message.delete()
        data = await state.get_data()
        id_new_admin = data.get("id_new_admin")

        if call.data.startswith("ConfirmChange_"):

            if id_new_admin and id_group:
                cursor.execute('''UPDATE KNEU SET admin_group = ? WHERE id = ?''', (id_new_admin, id_group))
                conn.commit()
                await call.message.answer(f"Адміністратор успішно змінений. Дякую за Вашу службу 🫡")
            else:
                await call.message.answer("Сталася помилка під час зміни адміністратора. Перевірте, чи є ID користувача та групи.")
        else:
            await call.message.answer("Скасування зміни адміністратора")
            await call.message.answer("Повертаємося до головного меню.", reply_markup=AdminKeyboard(id_group))

        await state.clear()
    except Exception as e:
        await call.message.answer(f"Виникла помилка: <code>{e}</code>. <b>ID: 31</b>. Задля її усунення зверніться будь ласка до @Zakhiel")        

@form_router.message(Command("help"))
async def Help(message: Message):
    try:
        await message.answer("Натисніть кнопку, щоб відкрити <b>документацію</b>", reply_markup=HelpKb())
    except Exception as e:
        await message.answer(f"Виникла помилка: <code>{e}</code>. <b>ID: 32.</b> Задля її вирішення, будь ласка, зв'яжіться з @Zakhiel")

async def main():
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(form_router)

    await dp.start_polling(bot)

if __name__ == "__main__": #І запускаємо Ійого
    logging.basicConfig(level=logging.INFO, stream=sys.stdout) #Вивід в консоль

    asyncio.run(main())