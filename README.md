# 🤖 KNEU sender

## ✅ Introduction

This Telegram bot is designed to assist students by providing easy access to up-to-date information regarding class schedules, links to online sessions, and instructors' email addresses. It also allows group administrators to configure these parameters directly within the bot.


## 🎯 Main features

**Providing the Current Class Schedule:** The bot provides users in the group with the current schedule for each day of the week.

**Links to Classes:** Users can get links to online classes.

**Instructors' Emails:** The bot provides information about the email addresses of instructors for easy communication.

**Administration Functions:** Group administrators can configure the schedule, class links, and instructors' emails through an interactive menu in the bot.


## ⚒ Instalation

**First step:** Clone the Repository

```
git clone https://github.com/wai-AI/Timetable-sender.git
cd Timetable-sender
```


**Second step:** Install Dependencies

```
pip install -r requirements.txt
```


**Third step:** Bot Configuration

Create a bot through BotFather and obtain the token.
Create a .json file in the project's root directory and add your token:

```
{
"BOT_TOKEN" : "your_bot_token_here"
}
```


**Fourth step:** Run the Bot

```
python main.py
```


## 🤖 Main Bot Commands

```/start```- Start interacting with the bot. Displays a welcome message. Works only in groups.

```/configure``` - Command for administrators. Opens the bot settings menu. Works only in private messages.

```/help``` - Help command. Displays documentation for bots' using.


## 👑 Administrator Interaction

**Add the Bot to a Group:** Add the bot to the group where you want to display timetaable, emails and links.

**Work with bot in a group:** Enter <code>/start</code> command to the group chat and following to the bots' instructions.

**Bots' configure:** Go to private messages to the bot and enter the <code>/configure</code> command.

**Documentation:** If you are needing any help with bot - you can send a <code>/help</code> command and read documentation.


## ⚖️ Licence

This project is licensed under the MIT License - see the LICENSE file for details.
