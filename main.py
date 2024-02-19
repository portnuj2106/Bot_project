
import asyncio
import logging
from http import HTTPStatus

import uvicorn
from asgiref.wsgi import WsgiToAsgi
from flask import Flask, Response, request

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)

from handlers.user_handlers import CustomContext, start, delete, echo

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

URL = "https://3399-46-63-28-245.ngrok-free.app"
ADMIN_CHAT_ID = 123456
PORT = 8000
TOKEN = "6975785463:AAH716QilWD2HXs7i3lXgE_DQPoKjkIgG78"


async def main() -> None:
    context_types = ContextTypes(context=CustomContext)
    application = (
        Application.builder().token(TOKEN).updater(None).context_types(context_types).build()
    )
    # register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("delete", delete))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    await application.bot.set_webhook(url=f"{URL}/telegram", allowed_updates=Update.ALL_TYPES)

    flask_app = Flask(__name__)

    @flask_app.post("/telegram")  # type: ignore[misc]
    async def telegram() -> Response:
        await application.update_queue.put(Update.de_json(data=request.json, bot=application.bot))
        return Response(status=HTTPStatus.OK)


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
