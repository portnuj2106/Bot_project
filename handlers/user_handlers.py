
from dataclasses import dataclass

import sqlite3
from telegram import Update
from telegram.ext import (
    Application,
    CallbackContext,
    ContextTypes,
    ExtBot,
)

@dataclass
class WebhookUpdate:
    user_id: int


class CustomContext(CallbackContext[ExtBot, dict, dict, dict]):
    @classmethod
    def from_update(
        cls,
        update: object,
        application: "Application",
    ) -> "CustomContext":
        if isinstance(update, WebhookUpdate):
            return cls(application=application, user_id=update.user_id)
        return super().from_update(update, application)


async def start(update: Update, context: CustomContext) -> None:
    """Display a message with instructions on how to use this bot."""
    conn = sqlite3.connect('users.db', check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute("""CREATE TABLE IF NOT EXISTS users_data (
                id INTEGER PRIMARY KEY,
                first_name TEXT Default '',
                last_name TEXT Default '',
                telegram_username TEXT Default ''
                    )""")
    conn.commit()

    cursor.execute(f"SELECT id FROM users_data WHERE id = {update.message.chat.id}")
    data = cursor.fetchone()
    if data is None:
        user_id = update.message.chat.id
        first_name = update.message.from_user.first_name  # Getting user's first name
        last_name = update.message.from_user.last_name  # Getting user's last name
        telegram_username = update.message.from_user.username  # Getting user's Telegram username

        cursor.execute("INSERT INTO users_data (id, first_name, last_name, telegram_username) VALUES (?, ?, ?, ?)",
                       (user_id, first_name, last_name, telegram_username))
        conn.commit()
        await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")
    else:

        await context.bot.send_message(chat_id=update.effective_chat.id, text="This user already exists")


async def delete(update: Update, context: CustomContext) -> None:
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    userid = update.message.chat.id
    cursor.execute(f"DELETE FROM users_data WHERE id = {userid}")
    conn.commit()
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Deleted successfully")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)

