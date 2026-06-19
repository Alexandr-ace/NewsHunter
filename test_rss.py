import requests
import feedparser
import telebot
import threading
import time

BOT_TOKEN = "ВСТАВЬ_СВОЙ_ТЕЛЕГРАМ_ТОКЕН"
url = "https://habr.com/ru/rss/all/all/?fl=ru"
bot = telebot.TeleBot(BOT_TOKEN)
alerts = {}  # {chat_id: target_price}

response = requests.get(url)
v = feedparser.parse(response.text)

keywords = ['python', 'fastapi', 'docker', 'telegram']

def filter_news(feed):
    found_count = 0
    for entry in feed.entries:
        title = entry.title.lower()
        summary = entry.summary.lower()
        
        for keyword in keywords:
            if keyword in title or keyword in summary:
                print(f"✅ Найдено совпадение: {keyword}")
                print(f"📰 {entry.title}")
                print(f"🔗 {entry.link}\n")
                found_count += 1
                break
    
    if found_count == 0:
        print("❌ Новостей с ключевыми словами не найдено")
    else:
        print(f"📊 Всего найдено: {found_count} новостей")

filter_news(v)