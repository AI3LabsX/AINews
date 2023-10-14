import asyncio
import os
import threading

from telegram.constants import ParseMode
from telegram.ext import AIORateLimiter, Application, Defaults

from core.logger import logger
from tg.bot_command import set_default_commands
from tg.handlers import HANDLERS
from tg.handlers.errors import error_handler
from tg.handlers.logic import monitor_feed


TELEGRAM_TOKEN = os.environ.get('BOT_TOKEN')

stop_event = threading.Event()  # Use a threading.Event to signal when to stop the bot


def start_bot_in_thread():
    loop = asyncio.new_event_loop()  # Create a new event loop
    asyncio.set_event_loop(loop)  # Set the new event loop as the default for this thread

    application = (
        Application.builder()
        .token(token=TELEGRAM_TOKEN)
        .defaults(defaults=Defaults(parse_mode=ParseMode.HTML, block=False))
        .rate_limiter(rate_limiter=AIORateLimiter(max_retries=3))
        .post_init(post_init=on_startup)
        .build()
    )

    register_all_handlers(application=application)
    loop.run_until_complete(application.run_polling(drop_pending_updates=True))  # Use the new event loop to run the bot
    stop_event.set()  # Signal the main thread to stop when the bot stops

async def on_startup(application: Application) -> None:
    await set_default_commands(application=application)


def register_all_handlers(application: Application) -> None:
    application.add_handlers(handlers=HANDLERS)
    application.add_error_handler(callback=error_handler)


async def main():
    bot_thread = threading.Thread(target=start_bot_in_thread)
    bot_thread.start()
    await monitor_feed()
    stop_event.set()  # Signal the bot to stop


if __name__ == "__main__":
    try:
        logger.info("Starting bot")
        asyncio.run(main())
    except Exception as exc:
        logger.critical("Unhandled error: %s", repr(exc))
    finally:
        stop_event.wait()  # Wait for the bot to stop
        logger.info("Bot stopped!")
