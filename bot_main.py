# import asyncio
# import os
# from threading import Thread
#
# from telegram.constants import ParseMode
# from telegram.ext import AIORateLimiter, Application, Defaults
#
# from core.logger import logger
# from tg.bot_command import set_default_commands
# from tg.handlers import HANDLERS
# from tg.handlers.errors import error_handler
# from tg.handlers.logic import monitor_feed
# os.environ["BOT_TOKEN"] = "6457071517:AAEE34Y-hnbKRnSaG7XR6OhlSB4hVh-_lzI"
# TELEGRAM_TOKEN = os.environ.get('BOT_TOKEN')
#
#
# def start_bot_in_thread(application: Application):
#     asyncio.set_event_loop(asyncio.new_event_loop())
#     application.run_polling(drop_pending_updates=True)
#
#
# async def on_startup(application: Application) -> None:
#     """
#     The function that runs when the bot starts, before the application.run_polling()
#     In this example, the function sets the default commands for the bot
#     """
#     await set_default_commands(application=application)
#
#
# def register_all_handlers(application: Application) -> None:
#     """Registers handlers"""
#
#     application.add_handlers(handlers=HANDLERS)
#     application.add_error_handler(callback=error_handler)
#
#
# async def start_bot():
#     application = (
#         Application.builder()
#         .token(token=TELEGRAM_TOKEN)
#         .defaults(defaults=Defaults(parse_mode=ParseMode.HTML, block=False))
#         .rate_limiter(rate_limiter=AIORateLimiter(max_retries=3))
#         .post_init(post_init=on_startup)
#         .build()
#     )
#
#     register_all_handlers(application=application)
#     thread = Thread(target=start_bot_in_thread, args=(application,))
#     thread.start()
#
#
# async def main():
#     await start_bot()  # This will start the bot in a separate thread
#     await monitor_feed()  # This will run in the main thread's event loop
#
#
# if __name__ == "__main__":
#     try:
#         logger.info("Starting bot")
#         asyncio.run(main())
#     except Exception as exc:
#         logger.critical("Unhandled error: %s", repr(exc))
#     finally:
#         logger.info("Bot stopped!")

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
