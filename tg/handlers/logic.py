# Initialize OpenAI
import asyncio
import datetime
import json
import os
from typing import Dict, Optional, Any

import feedparser
import openai
import psycopg2
import requests
import tiktoken
from aiohttp import ClientSession
from bs4 import BeautifulSoup
from dateutil import parser
from telegram import Bot
from telegram.constants import ParseMode

from core import PROJECT_ROOT
from core.logger import logger

openai.api_key = os.environ.get('OPENAI_API_KEY')
TELEGRAM_TOKEN = os.environ.get('BOT_TOKEN')
TELEGRAM_CHANNEL = '@ai3daily'

RETRY_COUNT = 3  # Number of times to retry processing an article if it fails
DATABASE_URL = os.environ.get('DATABASE_URL')
conn = psycopg2.connect(DATABASE_URL, sslmode='require')


def init_db():
    """Initialize the database and create the table if it doesn't exist."""
    with conn.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS latest_articles (
                rss_url TEXT PRIMARY KEY,
                pub_date TIMESTAMP
            );
        """)
    conn.commit()


init_db()


async def is_article_related_to_ai(title: str, content: str) -> bool:
    data = {
        "model": "gpt-3.5-turbo-16k",
        "messages": [
            {
                "role": "system",
                "content": "You are a filter bot. Determine if the provided article title and content are related to "
                           "AI, ML, DL. Return 'True' if it is related and 'False' if not related. Try to be precise "
                           "to filter all articles out, which are not related to AI. "
            },
            {
                "role": "user",
                "content": f"Article Title: {title}. Article Content: {content}"
            }
        ]
    }
    response = await openai.ChatCompletion.acreate(**data)
    answer = response['choices'][0]['message']['content']
    logger.info(answer)
    return answer.strip().lower() == 'true'


def get_final_url(url: str) -> str:
    if "news.google.com" in url:
        response = requests.get(url, allow_redirects=True)
        return response.url
    return url


def sanitize_text_for_telegram(text: str) -> str:
    sanitized_text = text.replace("<br>", "")
    return sanitized_text


def extract_largest_text_block(soup: BeautifulSoup) -> str:
    paragraphs = soup.find_all('p')
    largest_block = ""
    current_block = ""
    for paragraph in paragraphs:
        if len(paragraph.text) > 50:
            current_block += paragraph.text + "\n"
        else:
            if len(current_block) > len(largest_block):
                largest_block = current_block
            current_block = ""
    return largest_block.strip()


async def send_to_telegram(news_object: Dict[str, str]):
    logger.info(f"Sending news: {news_object['title']} to Telegram...")
    bot = Bot(token=TELEGRAM_TOKEN)
    sanitized_summary = news_object['summary'].replace("<the>", "").replace("</the>", "")
    sanitized_title = sanitize_text_for_telegram(news_object['title'])
    caption = f"<b>{sanitized_title}</b>\n\n{sanitized_summary}\n\n<a href='{news_object['url']}'>Read More</a>"
    if news_object['image']:
        await bot.send_photo(chat_id=TELEGRAM_CHANNEL, photo=news_object['image'], caption=caption,
                             parse_mode=ParseMode.HTML)
    else:
        await bot.send_message(chat_id=TELEGRAM_CHANNEL, text=caption, parse_mode=ParseMode.HTML)


def tiktoken_len(text: str) -> int:
    tokenizer = tiktoken.get_encoding('cl100k_base')
    tokens = tokenizer.encode(text, disallowed_special=())
    return len(tokens)


async def summarize_content(session: ClientSession, title: str, content: str) -> str:
    logger.info(f"Summarizing content for title: {title}...")
    data = {
        "model": "gpt-3.5-turbo-16k",
        "messages": [
            {
                "role": "system",
                "content": "You are Richard Rex, an AI engineer from PwC known for your wit and humor. Your goal is "
                           "to simplify AI news into short and cosine telegram posts with a blend of humor, sarcasm, "
                           "and insight. When analyzing news, craft a response in line with the following moods or a "
                           "mix of them:\n\n- **Cheerful**: Optimistic with light humor.\n- **Sarcastic**: Witty "
                           "remarks highlighting ironies.\n- **Contemplative**: Reflective with a touch of humor.\n- "
                           "**Humorous**: Full of laughter and playful analogies.\n- **Serious**: Grave, with a hint "
                           "of sarcasm.\n\nMoods can combine or vary in intensity, e.g., 'slightly humorous' or 'very "
                           "sarcastic'. Aim for concise and short responses, around 100-150 words maximum, "
                           "that are engaging and in character. Your output should be the post text without "
                           "mentioning the mood."
            },
            {
                "role": "system",
                "content": " Try to be as short as possible with an average post-token "
                           "length of around 100 tokens, while keeping the personality. Final Response:As Output, "
                           "you have to provide only post text, do not provide mood choice in response. "
            },
            {
                "role": "user",
                "content": f"News Title: {title}. News Content: {content}"
            }

        ],
        "temperature": 0.7,
        "max_tokens": 300,
        "top_p": 0.4,
        "frequency_penalty": 1.5,
        "presence_penalty": 1
    }

    response = await openai.ChatCompletion.acreate(**data)
    summary = response['choices'][0]['message']['content']

    # Second request
    data["messages"][1]["content"] = f"Make the text below better structured for the telegram channel post, " \
                                     f"so it looks beautiful. Do not change content, add bold HTML tags <b>Example</b> for " \
                                     f"essential keywords in text to make it easier to read (Just put essential " \
                                     f"keywords between b tags). Do not add emojis in the text.\nNew Post: {summary}"
    print(data)
    response = await openai.ChatCompletion.acreate(**data)
    bolded_summary = response['choices'][0]['message']['content']
    print(bolded_summary)
    return bolded_summary


def parse_pub_date(pub_date_str: str) -> parser:
    if isinstance(pub_date_str, str):
        return parser.parse(pub_date_str)
    elif isinstance(pub_date_str, datetime.datetime):
        return pub_date_str
    else:
        raise ValueError(f"Unexpected type for pub_date_str: {type(pub_date_str)}")



async def fetch_latest_article_from_rss(session: ClientSession, rss_url: str, latest_pub_date, first_run=False) -> \
        Optional[Dict[str, Any]]:
    logger.info(f"Fetching latest article from RSS: {rss_url}...")
    feed = feedparser.parse(rss_url)
    articles = []
    for entry in feed.entries:
        pub_date = parse_pub_date(entry.published)
        if latest_pub_date and pub_date <= parse_pub_date(latest_pub_date):  # Parse the string into datetime
            continue
        title = entry.title
        link = entry.link
        final_link = get_final_url(link)
        page_response = await session.get(final_link)
        soup = BeautifulSoup(await page_response.text(), 'html.parser')
        content = extract_largest_text_block(soup)
        image_div = soup.find('figure', {'class': 'article__lead__image'})
        image_url = image_div.find('img')['src'] if image_div else None
        articles.append({
            "title": title,
            "link": link,
            "content": content,
            "pub_date": pub_date,
            "image": image_url
        })
    if first_run:
        if articles:  # Check if articles list is not empty
            return {"pub_date": articles[0]["pub_date"].isoformat()}  # Just return the timestamp during the first run
        else:
            return None
    return articles[0] if articles else None


async def process_rss_url(session: ClientSession, rss_url: str, latest_pub_dates: Dict[str, Any], first_run=False):
    logger.info(f"Processing RSS URL: {rss_url}...")
    retries = 0
    while retries < RETRY_COUNT:
        try:
            article = await fetch_latest_article_from_rss(session, rss_url, latest_pub_dates.get(rss_url), first_run)
            if first_run:
                latest_pub_dates[rss_url] = article["pub_date"]
                save_latest_pub_dates(latest_pub_dates)
                return
            if article:
                is_related = await is_article_related_to_ai(article['title'], article['content'])
                # Update the timestamp regardless of whether the article is AI-related or not
                latest_pub_dates[rss_url] = article["pub_date"].isoformat()
                save_latest_pub_dates(latest_pub_dates)

                if not is_related:
                    logger.info(f"Skipping non-AI related article: {article['title']}")
                    continue
                print(f"New article found: {article['title']}")
                summary = await summarize_content(session, article['title'], article['content'])
                news_object = {
                    "title": article['title'],
                    "url": article['link'],
                    "image": article['image'],
                    "summary": summary
                }
                await send_to_telegram(news_object)
            break
        except Exception as e:
            logger.error(f"Error processing RSS URL {rss_url}. Retrying... Error: {e}")
            retries += 1
            await asyncio.sleep(10)


def load_rss_feeds():
    with open(PROJECT_ROOT.joinpath("rss_feeds.json"), "r") as file:
        return json.load(file)


def load_latest_pub_dates():
    """Load the latest publication dates from the database."""
    with conn.cursor() as cursor:
        cursor.execute("SELECT rss_url, pub_date FROM latest_articles;")
        rows = cursor.fetchall()
        return {row[0]: row[1] for row in rows}


def save_latest_pub_dates(latest_pub_dates):
    """Save the latest publication dates to the database."""
    with conn.cursor() as cursor:
        for rss_url, pub_date in latest_pub_dates.items():
            cursor.execute("""
                INSERT INTO latest_articles (rss_url, pub_date)
                VALUES (%s, %s)
                ON CONFLICT (rss_url) DO UPDATE
                SET pub_date = %s;
            """, (rss_url, pub_date, pub_date))
    conn.commit()


async def monitor_feed():
    logger.info("Starting to monitor feeds...")
    rss_feeds = load_rss_feeds()
    rss_urls = list(rss_feeds.keys())
    latest_pub_dates = load_latest_pub_dates()
    first_run = not bool(latest_pub_dates)  # Check if it's the first run
    while True:
        updated_rss_feeds = load_rss_feeds()
        updated_rss_urls = list(updated_rss_feeds.keys())
        for rss_url in updated_rss_urls:
            if rss_url not in rss_urls:
                rss_urls.append(rss_url)
                if rss_url not in latest_pub_dates:
                    latest_pub_dates[rss_url] = None
        for rss_url in rss_urls:
            if rss_url not in updated_rss_urls:
                rss_urls.remove(rss_url)
                if rss_url in latest_pub_dates:
                    del latest_pub_dates[rss_url]
        async with ClientSession() as session:
            if first_run:  # If it's the first run, just update the latest article timestamps
                tasks = [process_rss_url(session, rss_url, latest_pub_dates, first_run=True) for rss_url in rss_urls]
            else:
                tasks = [process_rss_url(session, rss_url, latest_pub_dates) for rss_url in rss_urls]
            await asyncio.gather(*tasks)
        if first_run:  # If it's the first run, update the flag after processing all feeds
            first_run = False
        await asyncio.sleep(300)
