import os
import html
import requests
from bs4 import BeautifulSoup

SOURCES = [
    "https://t.me/s/javohir_webdev",
    "https://t.me/s/mohirdev",
    "https://t.me/s/naxalov",
    "https://t.me/s/aicreatorsuz",
]

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TARGET = os.getenv("TELEGRAM_TARGET", "@teleposttestuz")

def latest_posts(url: str, limit: int = 3):
    r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    result = []
    for node in soup.select(".tgme_widget_message_text")[-limit:]:
        text = node.get_text("\n", strip=True)
        if text:
            result.append(text)
    return result

def collect():
    items = []
    for source in SOURCES:
        try:
            posts = latest_posts(source)
            items.extend((source, p) for p in posts)
        except Exception as e:
            print(f"Source failed: {source}: {e}")
    return items

def build_test_post(items):
    # Temporary bridge test: AI layer will be inserted separately.
    if not items:
        return "Bugun kuzatilgan kanallardan yangi kontent olinmadi."
    source, text = items[-1]
    clean = text[:2500]
    return (
        "📰 KUNLIK TEXNOLOGIYA SARALAMASI\n\n"
        f"{clean}\n\n"
        "Manba: " + source
    )

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    r = requests.post(
        url,
        json={
            "chat_id": TARGET,
            "text": text,
            "disable_web_page_preview": False,
        },
        timeout=30,
    )
    r.raise_for_status()
    print("Telegram:", r.json())

if __name__ == "__main__":
    items = collect()
    post = build_test_post(items)
    send_message(post)
