#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Channel Style Analyzer & Auto Poster Agent
Google Gemini API orqali
"""
import os
import json
import logging
import schedule
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai
from telegram import Bot
from telegram.error import TelegramError
import aiohttp
import asyncio

load_dotenv()

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("agent.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TARGET_CHANNEL = os.getenv("TARGET_CHANNEL", "@YOUR_CHANNEL")
TASK_INTERVAL_HOURS = int(os.getenv("TASK_INTERVAL_HOURS", "2"))
ANALYSIS_CHANNELS = ["AITOOL_UZ", "the_bakiroo"]
STYLES_FILE = "channel_styles.json"

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

bot = Bot(token=TELEGRAM_BOT_TOKEN) if TELEGRAM_BOT_TOKEN else None


class StyleAnalyzer:
    def __init__(self):
        self.model = genai.GenerativeModel("gemini-pro")
        self.styles = self.load_styles()

    def load_styles(self):
        if Path(STYLES_FILE).exists():
            with open(STYLES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_styles(self):
        with open(STYLES_FILE, "w", encoding="utf-8") as f:
            json.dump(self.styles, f, ensure_ascii=False, indent=2)

    async def analyze_channel_style(self, channel_username: str, sample_posts: list):
        posts_text = "\n---\n".join(sample_posts[-10:])
        prompt = f"""
Ushbu Telegram kanalining yozish stilini chuqur tahlil qil:
Kanal: @{channel_username}
Postlar:
{posts_text}

Quyidagilarni JSON formatida javob ber:
{{
  "tone": "postning toni",
  "emoji_style": "emoji qo'llash tarzi",
  "common_emojis": [],
  "sentence_structure": "gap tuzilishi",
  "language_features": "O'zbekcha yozish xususiyatlari",
  "topics": [],
  "formatting": "text formatlash",
  "post_length": "o'rtacha post uzunligi",
  "key_phrases": [],
  "hashtag_style": "hashtag qo'llash tarzi"
}}
Faqat JSON javob ber.
"""
        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:-3]
            elif text.startswith("```"):
                text = text[3:-3]
            data = json.loads(text)
            self.styles[channel_username] = data
            self.save_styles()
            return data
        except Exception as e:
            logger.error("Style analysis error: %s", e)
            return None

    def get_style(self, channel_username: str):
        return self.styles.get(channel_username, {})


class ContentGenerator:
    def __init__(self, analyzer: StyleAnalyzer):
        self.model = genai.GenerativeModel("gemini-pro")
        self.analyzer = analyzer

    async def generate_post(self, style_channels=None):
        style_channels = style_channels or ANALYSIS_CHANNELS
        combined_styles = {
            ch: self.analyzer.get_style(ch)
            for ch in style_channels
            if self.analyzer.get_style(ch)
        }
        style_description = json.dumps(combined_styles, ensure_ascii=False, indent=2)
        prompt = f"""
Ushbu stillar bo'yicha Telegram kanalga yangi post yarat:
{style_description}

JSON qaytar:
{{
  "text": "Post matni",
  "image_prompt": "English image prompt",
  "hashtags": [],
  "category": "mavzu kategoriyasi",
  "estimated_engagement": "1-10"
}}
Matn O'zbekcha va jozibador bo'lsin. Faqat JSON javob ber.
"""
        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:-3]
            elif text.startswith("```"):
                text = text[3:-3]
            return json.loads(text)
        except Exception as e:
            logger.error("Content generation error: %s", e)
            return None


class ChannelMonitor:
    async def get_recent_posts(self, channel_username: str, limit: int = 20):
        try:
            url = f"https://t.me/s/{channel_username}/1"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        return await self.get_sample_posts(channel_username)
            return []
        except Exception as e:
            logger.error("Post loading error (%s): %s", channel_username, e)
            return []

    async def get_sample_posts(self, channel_username: str):
        samples = {
            "AITOOL_UZ": [
                "AI yangiliklari va yangi texnologiyalar",
                "Eng so'nggi AI tools va servislar",
                "Kod yozish uchun AI vositalari",
                "Agentic AI va zamonaviy modellar",
                "ChatGPT, Claude, Gemini farqlari",
            ],
            "the_bakiroo": [
                "Hayot haqida fikrlar",
                "Insoniy munosabatlar haqida",
                "Kichik qadamlar katta natijalarga olib keladi",
                "O'z yo'lingizni topdingizmi?",
                "Yaxshi kitob tavsiyasi",
            ],
        }
        return samples.get(channel_username, [])


class AutoPoster:
    async def post_to_channel(self, channel_id: str, text: str, image_url: str = None):
        if not bot:
            logger.warning("TELEGRAM_BOT_TOKEN topilmadi")
            return False
        try:
            if image_url:
                await bot.send_photo(chat_id=channel_id, photo=image_url, caption=text, parse_mode="HTML")
            else:
                await bot.send_message(chat_id=channel_id, text=text, parse_mode="HTML")
            return True
        except TelegramError as e:
            logger.error("Post yuborish xatosi: %s", e)
            return False


class TelegramAgent:
    def __init__(self):
        self.analyzer = StyleAnalyzer()
        self.generator = ContentGenerator(self.analyzer)
        self.monitor = ChannelMonitor()
        self.poster = AutoPoster()
        self.is_running = False

    async def initialize(self):
        for channel in ANALYSIS_CHANNELS:
            posts = await self.monitor.get_recent_posts(channel)
            if posts:
                await self.analyzer.analyze_channel_style(channel, posts)

    async def run_task(self):
        logger.info("Task boshlandi: %s", datetime.now().isoformat())
        try:
            content = await self.generator.generate_post()
            if content:
                with open("generated_content.json", "w", encoding="utf-8") as f:
                    json.dump(content, f, ensure_ascii=False, indent=2)
                logger.info("Kontent saqlandi")
        except Exception as e:
            logger.error("Task xatosi: %s", e)

    def start(self):
        asyncio.run(self.initialize())
        schedule.every(TASK_INTERVAL_HOURS).hours.do(lambda: asyncio.run(self.run_task()))
        self.is_running = True
        while self.is_running:
            schedule.run_pending()
            time.sleep(60)


def main():
    if not TELEGRAM_BOT_TOKEN or not GEMINI_API_KEY:
        logger.error("TELEGRAM_BOT_TOKEN va GEMINI_API_KEY environment variablelari kerak")
        return
    TelegramAgent().start()


if __name__ == "__main__":
    main()
