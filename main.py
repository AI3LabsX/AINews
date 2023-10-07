import asyncio
import time

import feedparser
import openai
import requests
from dateutil import parser
from langchain.document_loaders import AsyncChromiumLoader
from langchain.document_transformers import BeautifulSoupTransformer
from telegram import Bot
from telegram.constants import ParseMode

from core.env import env

# Initialize OpenAI
openai.api_key = env.get_openai_api()
TELEGRAM_TOKEN = env.get_token_or_exit()
TELEGRAM_CHANNEL = '@ai3daily'  # Replace 'yourchannelname' with your channel's name

rss_urls = [
    "https://aws.amazon.com/blogs/machine-learning/feed/",
    "https://news.mit.edu/rss/topic/artificial-intelligence2",
    "https://techcrunch.com/feed/",
    "https://openai.com/blog/rss.xml"
]


def get_final_url(url):
    if "news.google.com" in url:
        response = requests.get(url, allow_redirects=True)
        return response.url
    return url


async def send_to_telegram(news_object):
    bot = Bot(token=TELEGRAM_TOKEN)
    caption = f"<b>{news_object['title']}</b>\n\n{news_object['summary']}\n\n<a href='{news_object['url']}'>Read More</a>"
    if news_object['image']:
        await bot.send_photo(chat_id=TELEGRAM_CHANNEL, photo=news_object['image'], caption=caption,
                             parse_mode=ParseMode.HTML)
    else:
        await bot.send_message(chat_id=TELEGRAM_CHANNEL, text=caption, parse_mode=ParseMode.HTML)


def summarize_content(title, content):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-16k",
        messages=[
            {
                "role": "system",
                "content": "You are a news summarizer bot. Extract only essential key points from the provided news content. Try to be short and concise, giving essential summary points that cover all main news ideas, but still should have some context to fully cover the news content."
            },
            {
                "role": "user",
                "content": f"News Title: {title}. News Content: {content}"
            }
        ],
        temperature=0,
        max_tokens=300,
        top_p=0.4,
        frequency_penalty=1.5,
        presence_penalty=1
    )
    summary = response['choices'][0]['message']['content']

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "You are a helper bot. Please bold the essential words in the provided summary using HTML tags. <b> </b>"
            },
            {
                "role": "user",
                "content": f"Please bold the essential words in this summary: {summary}"
            }
        ],
        temperature=0,
        max_tokens=300,
        top_p=0.4,
        frequency_penalty=1.5,
        presence_penalty=1
    )
    bolded_summary = response['choices'][0]['message']['content']
    return bolded_summary


def parse_pub_date(pub_date_str):
    return parser.parse(pub_date_str)


def fetch_latest_article_from_rss(rss_url):
    feed = feedparser.parse(rss_url)
    if not feed.entries:
        return None

    entry = feed.entries[0]
    title = entry.title
    link = entry.link
    final_link = get_final_url(link)

    # Use AsyncChromiumLoader to load the HTML
    loader = AsyncChromiumLoader([final_link])
    html = loader.load()

    # Use BeautifulSoupTransformer to extract content
    bs_transformer = BeautifulSoupTransformer()
    docs_transformed = bs_transformer.transform_documents(html, tags_to_extract=["span"])
    content = docs_transformed[0].page_content

    return {
        "title": title,
        "link": link,
        "content": content,
        "pub_date": parse_pub_date(entry.published),
        "image": None  # You can modify this to extract the image using BeautifulSoup if needed
    }


def monitor_feed():
    latest_pub_dates = {rss_url: None for rss_url in rss_urls}
    loop = asyncio.get_event_loop()

    while True:
        for rss_url in rss_urls:
            print(f"Checking for new articles from {rss_url}...")
            article = fetch_latest_article_from_rss(rss_url)

            if article:
                print(f"New article found: {article['title']}")
                latest_pub_dates[rss_url] = article["pub_date"]
                summary = summarize_content(article['title'], article['content'])
                news_object = {
                    "title": article['title'],
                    "url": article['link'],
                    "image": article['image'],
                    "summary": summary
                }
                loop.run_until_complete(send_to_telegram(news_object))

        time.sleep(10)


if __name__ == "__main__":
    monitor_feed()
