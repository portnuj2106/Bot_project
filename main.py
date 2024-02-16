
import asyncio
import html
import logging
from dataclasses import dataclass
from http import HTTPStatus

import uvicorn
from asgiref.wsgi import WsgiToAsgi
from flask import Flask, Response, abort, make_response, request

import sqlite3
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackContext,
    CommandHandler,
    ContextTypes,
    ExtBot,
    TypeHandler,
    MessageHandler,
    filters
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

URL = "https://cd25-46-63-28-245.ngrok-free.app"
ADMIN_CHAT_ID = 123456
PORT = 8000
TOKEN = "6975785463:AAH716QilWD2HXs7i3lXgE_DQPoKjkIgG78"  # nosec B105


@dataclass
class WebhookUpdate:
    user_id: int
    payload: str
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


async def webhook_update(update: WebhookUpdate, context: CustomContext) -> None:
    """Handle custom updates."""
    chat_member = await context.bot.get_chat_member(chat_id=update.user_id, user_id=update.user_id)
    payloads = context.user_data.setdefault("payloads", [])
    payloads.append(update.payload)
    combined_payloads = "</code>\n• <code>".join(payloads)
    text = (
        f"The user {chat_member.user.mention_html()} has sent a new payload. "
        f"So far they have sent the following payloads: \n\n• <code>{combined_payloads}</code>"
    )
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=text, parse_mode=ParseMode.HTML)


async def main() -> None:
    """Set up PTB application and a web application for handling the incoming requests."""
    context_types = ContextTypes(context=CustomContext)
    # Here we set updater to None because we want our custom webhook server to handle the updates
    # and hence we don't need an Updater instance
    application = (
        Application.builder().token(TOKEN).updater(None).context_types(context_types).build()
    )


    # register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("delete", delete))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    application.add_handler(TypeHandler(type=WebhookUpdate, callback=webhook_update))


    await application.bot.set_webhook(url=f"{URL}/telegram", allowed_updates=Update.ALL_TYPES)


    flask_app = Flask(__name__)

    @flask_app.post("/telegram")  # type: ignore[misc]
    async def telegram() -> Response:
        await application.update_queue.put(Update.de_json(data=request.json, bot=application.bot))
        return Response(status=HTTPStatus.OK)

    @flask_app.route("/submitpayload", methods=["GET", "POST"])  # type: ignore[misc]
    async def custom_updates() -> Response:

        try:
            user_id = int(request.args["user_id"])
            payload = request.args["payload"]
        except KeyError:
            abort(
                HTTPStatus.BAD_REQUEST,
                "Please pass both `user_id` and `payload` as query parameters.",
            )
        except ValueError:
            abort(HTTPStatus.BAD_REQUEST, "The `user_id` must be a string!")

        await application.update_queue.put(WebhookUpdate(user_id=user_id, payload=payload))
        return Response(status=HTTPStatus.OK)

    @flask_app.get("/healthcheck")  # type: ignore[misc]
    async def health() -> Response:
        response = make_response("The bot is still running fine :)", HTTPStatus.OK)
        response.mimetype = "text/plain"
        return response

    @flask_app.route("/")
    async def index():
        return "Hello, World!"

    webserver = uvicorn.Server(
        config=uvicorn.Config(
            app=WsgiToAsgi(flask_app),
            port=PORT,
            use_colors=False,
            host="127.0.0.1",
        )
    )

    async with application:
        await application.start()
        await webserver.serve()
        await application.stop()


if __name__ == "__main__":
    asyncio.run(main())