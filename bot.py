import json
import os
from datetime import datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup

from ai_engine import generate

ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(ROOT, "config", "sources.json")
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TARGET = os.getenv("TELEGRAM_TARGET", "@teleposttestuz")


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def collect():
    config = load_config()
    sources = config.get("telegram_sources", [])
    max_posts = int(config.get("max_posts_per_source", 5))
    lookback_days = int(config.get("lookback_days", 7))
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    items = []

    for source in sources:
        try:
            r = requests.get(source, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            for node in soup.select(".tgme_widget_message")[-max_posts:]:
                t = node.select_one(".tgme_widget_message_text")
                if not t:
                    continue
                text = t.get_text("\n", strip=True)
                if not text:
                    continue
                d = node.select_one(".tgme_widget_message_date")
                url = d.get("href") if d else source
                post_date = None
                tm = node.select_one("time[datetime]")
                if tm and tm.get("datetime"):
                    try:
                        post_date = datetime.fromisoformat(tm.get("datetime").replace("Z", "+00:00"))
                    except ValueError:
                        pass
                if post_date and post_date < cutoff:
                    continue
                items.append({"url": url or source, "text": text[:5000]})
        except requests.RequestException as e:
            print("Source failed:", source, e)
        except Exception as e:
            print("Source parse failed:", source, e)
    return items


def send(text):
    if not text:
        raise RuntimeError("Generated post is empty")
    r = requests.post(
        "https://api.telegram.org/bot" + TOKEN + "/sendMessage",
        json={"chat_id": TARGET, "text": text, "disable_web_page_preview": False},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError("Telegram API error: " + json.dumps(data, ensure_ascii=False))
    print("Telegram publish: success")


if __name__ == "__main__":
    items = collect()
    print("Collected:", len(items))
    if not items:
        print("No recent source posts found; nothing to publish.")
        raise SystemExit(0)

    result = generate(items)
    print("ANALYSIS:", json.dumps(result.get("analysis", {}), ensure_ascii=False))
    print("IMAGE PROMPT:", result.get("image_prompt", ""))

    if str(result.get("status", "REJECT")).upper() != "PUBLISH":
        print("Content rejected by quality gate.")
        raise SystemExit(0)

    post = str(result.get("post", "")).strip()
    source_url = str(result.get("source_url", "")).strip()
    if source_url and source_url not in post:
        post += "\n\n👉 Manba: " + source_url
    send(post)
