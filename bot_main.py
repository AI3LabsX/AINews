import asyncio
import os

from telegram.constants import ParseMode
from telegram.ext import AIORateLimiter, Application, Defaults

from core.logger import logger
from tg.bot_command import set_default_commands
from tg.handlers import HANDLERS
from tg.handlers.errors import error_handler
from tg.handlers.logic import monitor_feed

TELEGRAM_TOKEN = os.environ.get('BOT_TOKEN')


async def start_bot():
    application = (
        Application.builder()
        .token(token=TELEGRAM_TOKEN)
        .defaults(defaults=Defaults(parse_mode=ParseMode.HTML, block=False))
        .rate_limiter(rate_limiter=AIORateLimiter(max_retries=3))
        .post_init(post_init=on_startup)
        .build()
    )

    register_all_handlers(application=application)
    await application.run_polling(drop_pending_updates=True)


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


async def main():
    bot_task = asyncio.create_task(start_bot())
    monitor_task = asyncio.create_task(monitor_feed())
    await asyncio.gather(bot_task, monitor_task)


if __name__ == "__main__":
    try:
        logger.info("Starting bot")
        asyncio.run(main())
    except Exception as exc:
        logger.critical("Unhandled error: %s", repr(exc))
    finally:
        logger.info("Bot stopped!")
