import json

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler

from core import PROJECT_ROOT


# Callback function to handle button presses
async def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    rss_url = query.data

    with open(PROJECT_ROOT.joinpath("rss_feeds.json"), "r+") as file:
        feeds = json.load(file)
        if rss_url in feeds:
            del feeds[rss_url]
            file.seek(0)
            file.truncate()
            json.dump(feeds, file)
            await query.edit_message_text(text=f"Deleted RSS feed: {rss_url}")
        else:
            await query.edit_message_text(text="RSS feed not found!")


async def add(update: Update, context: CallbackContext) -> None:
    # Assuming the format is /add name url
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /add name url")
        return

    url, name = context.args
    with open(PROJECT_ROOT.joinpath("rss_feeds.json"), "r+") as file:
        feeds = json.load(file)
        feeds[url] = name
        file.seek(0)
        file.truncate()
        json.dump(feeds, file)

    await update.message.reply_text(f"Added RSS feed: {name}")
    # latest_pub_dates = {url: None}
    # while True:
    #     async with ClientSession() as session:
    #         await process_rss_url(session, url, latest_pub_dates)


async def delete(update: Update, context: CallbackContext) -> None:
    with open(PROJECT_ROOT.joinpath("rss_feeds.json"), "r") as file:
        feeds = json.load(file)

    keyboard = []
    for rss_url, name in feeds.items():
        keyboard.append([InlineKeyboardButton(name, callback_data=rss_url)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Select the RSS feed to delete:', reply_markup=reply_markup)


add_handler: CommandHandler = CommandHandler(
    command="add", callback=add)

delete_handler: CommandHandler = CommandHandler(
    command="delete", callback=delete)

button_handler: CallbackQueryHandler = CallbackQueryHandler(callback=button)
