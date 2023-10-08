import asyncio
from threading import Thread

from telegram.constants import ParseMode
from telegram.ext import AIORateLimiter, Application, Defaults

from core.env import env
from core.logger import logger
from tg.bot_command import set_default_commands
from tg.handlers import HANDLERS
from tg.handlers.errors import error_handler
from tg.handlers.logic import monitor_feed


def start_bot_in_thread(application: Application):
    asyncio.set_event_loop(asyncio.new_event_loop())
    application.run_polling(drop_pending_updates=True)


async def on_startup(application: Application) -> None:
    """
    The function that runs when the bot starts, before the application.run_polling()
    In this example, the function sets the default commands for the bot
    """
    await set_default_commands(application=application)


def register_all_handlers(application: Application) -> None:
    """Registers handlers"""

    application.add_handlers(handlers=HANDLERS)
    application.add_error_handler(callback=error_handler)


async def start_bot():
    application = (
        Application.builder()
        .token(token=env.get_token_or_exit())
        .defaults(defaults=Defaults(parse_mode=ParseMode.HTML, block=False))
        .rate_limiter(rate_limiter=AIORateLimiter(max_retries=3))
        .post_init(post_init=on_startup)
        .build()
    )

    register_all_handlers(application=application)
    thread = Thread(target=start_bot_in_thread, args=(application,))
    thread.start()


async def main():
    await start_bot()  # This will start the bot in a separate thread
    await monitor_feed()  # This will run in the main thread's event loop


if __name__ == "__main__":
    try:
        logger.info("Starting bot")
        asyncio.run(main())
    except Exception as exc:
        logger.critical("Unhandled error: %s", repr(exc))
    finally:
        logger.info("Bot stopped!")
