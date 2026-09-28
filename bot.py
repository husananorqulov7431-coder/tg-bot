import os
import requests
from bs4 import BeautifulSoup
from ai_engine import generate

SOURCES = ["https://t.me/s/javohir_webdev","https://t.me/s/mohirdev","https://t.me/s/naxalov","https://t.me/s/aicreatorsuz"]
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TARGET = os.getenv("TELEGRAM_TARGET", "@teleposttestuz")

def collect():
    items = []
    for source in SOURCES:
        try:
            r = requests.get(source, timeout=30, headers={"User-Agent":"Mozilla/5.0"})
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            for node in soup.select(".tgme_widget_message")[-5:]:
                t = node.select_one(".tgme_widget_message_text")
                if not t: continue
                text = t.get_text("\n", strip=True)
                if not text: continue
                d = node.select_one(".tgme_widget_message_date")
                items.append({"url": d.get("href") if d else source, "text": text[:5000]})
        except Exception as e:
            print("Source failed:", source, e)
    return items

def send(text):
    r = requests.post("https://api.telegram.org/bot" + TOKEN + "/sendMessage",
        json={"chat_id":TARGET,"text":text,"disable_web_page_preview":False}, timeout=30)
    r.raise_for_status()

if __name__ == "__main__":
    items = collect()
    print("Collected:", len(items))
    if items:
        result = generate(items)
        print("ANALYSIS:", result.get("analysis", {}))
        print("IMAGE PROMPT:", result.get("image_prompt", ""))
        if str(result.get("status","REJECT")).upper() == "PUBLISH":
            post = result.get("post","").strip()
            url = result.get("source_url","").strip()
            if url and url not in post: post += "\n\n👉 Manba: " + url
            send(post)
