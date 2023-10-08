# Initialize OpenAI
import asyncio
import json
from typing import Dict, Optional, Any

import feedparser
import openai
import requests
import tiktoken
from aiohttp import ClientSession
from bs4 import BeautifulSoup
from dateutil import parser
from telegram import Bot
from telegram.constants import ParseMode

from core import PROJECT_ROOT
from core.env import env
from core.logger import logger

openai.api_key = env.get_openai_api()
TELEGRAM_TOKEN = env.get_token_or_exit()
TELEGRAM_CHANNEL = '@ai3daily'

RETRY_COUNT = 3  # Number of times to retry processing an article if it fails


def get_final_url(url: str) -> str:
    if "news.google.com" in url:
        response = requests.get(url, allow_redirects=True)
        return response.url
    return url


def sanitize_text_for_telegram(text: str) -> str:
    # Remove or replace any unsupported HTML tags or entities
    sanitized_text = text.replace("<br>", "")  # replace <br> with a space
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

    # In your send_to_telegram function
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
                "content": "You are a news summarizer bot. Extract only essential key points from the provided news "
                           "content. Try to be short and concise, giving essential summary points that cover all main "
                           "news ideas, but still should have some context to fully cover the news content. "
            },
            {
                "role": "user",
                "content": f"News Title: {title}. News Content: {content}"
            }
        ],
        "temperature": 0,
        "max_tokens": 300,
        "top_p": 0.4,
        "frequency_penalty": 1.5,
        "presence_penalty": 1
    }
    response = await openai.ChatCompletion.acreate(**data)
    summary = response['choices'][0]['message']['content']

    # Second request
    data["messages"][1]["content"] = f"Highlight the essential keywords in the following summary by wrapping them " \
                                     f"with <b> and </b> tags. Summary: {summary} "
    print(data)
    response = await openai.ChatCompletion.acreate(**data)
    bolded_summary = response['choices'][0]['message']['content']
    print(bolded_summary)
    return bolded_summary


def parse_pub_date(pub_date_str: str) -> parser:
    return parser.parse(pub_date_str)


async def fetch_latest_article_from_rss(session: ClientSession, rss_url: str,
                                        latest_pub_date) -> Optional[Dict[str, Any]]:
    logger.info(f"Fetching latest article from RSS: {rss_url}...")
    feed = feedparser.parse(rss_url)
    articles = []

    for entry in feed.entries:
        pub_date = parse_pub_date(entry.published)
        if latest_pub_date and pub_date <= latest_pub_date:
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

    return articles[0] if articles else None


async def process_rss_url(session: ClientSession, rss_url: str, latest_pub_dates: Dict[str, Any]):
    logger.info(f"Processing RSS URL: {rss_url}...")
    retries = 0
    while retries < RETRY_COUNT:
        try:
            article = await fetch_latest_article_from_rss(session, rss_url, latest_pub_dates.get(rss_url))
            if article:
                print(f"New article found: {article['title']}")
                latest_pub_dates[rss_url] = article["pub_date"]
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
            await asyncio.sleep(10)  # Wait for 10 seconds before retrying


def load_rss_feeds():
    with open(PROJECT_ROOT.joinpath("rss_feeds.json"), "r") as file:
        return json.load(file)


async def monitor_feed():
    logger.info("Starting to monitor feeds...")

    # Initial load outside the loop
    rss_feeds = load_rss_feeds()
    rss_urls = list(rss_feeds.keys())
    latest_pub_dates = {rss_url: None for rss_url in rss_urls}

    while True:
        # Reload the rss_feeds.json file inside the loop
        updated_rss_feeds = load_rss_feeds()
        updated_rss_urls = list(updated_rss_feeds.keys())

        # Check for new feeds and update rss_urls and latest_pub_dates
        for rss_url in updated_rss_urls:
            if rss_url not in rss_urls:
                rss_urls.append(rss_url)
                latest_pub_dates[rss_url] = None

        # Check for deleted feeds and update rss_urls and latest_pub_dates
        for rss_url in rss_urls:
            if rss_url not in updated_rss_urls:
                rss_urls.remove(rss_url)
                del latest_pub_dates[rss_url]

        async with ClientSession() as session:
            tasks = [process_rss_url(session, rss_url, latest_pub_dates) for rss_url in rss_urls]
            await asyncio.gather(*tasks)

        await asyncio.sleep(10)

