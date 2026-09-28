import asyncio
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TARGET = os.getenv("TELEGRAM_TARGET", "@teleposttestuz").strip()
DATA_DIR = Path(os.getenv("DATA_DIR", str(ROOT / "data")))
DB_PATH = DATA_DIR / "bot.sqlite3"

RAW_IDS = os.getenv("ALLOWED_USER_IDS", "")
ALLOWED_IDS = {int(x.strip()) for x in RAW_IDS.split(",") if x.strip().isdigit()}

if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is missing")

DATA_DIR.mkdir(parents=True, exist_ok=True)

bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE IF NOT EXISTS tasks "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id INTEGER, text TEXT, "
        "status TEXT NOT NULL, created_at TEXT NOT NULL)"
    )
    conn.commit()
    return conn


def allowed(message: Message):
    return not ALLOWED_IDS or (
        message.from_user and message.from_user.id in ALLOWED_IDS
    )


def save_task(user_id: int, text: str) -> int:
    conn = db()
    cur = conn.execute(
        "INSERT INTO tasks(telegram_id,text,status,created_at) VALUES(?,?,?,?)",
        (user_id, text, "queued", datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    task_id = int(cur.lastrowid)
    conn.close()
    return task_id


def menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✍️ Post yaratish", callback_data="post"),
                InlineKeyboardButton(text="🔎 Research", callback_data="research"),
            ],
            [
                InlineKeyboardButton(text="💡 G‘oyalar", callback_data="ideas"),
                InlineKeyboardButton(text="🖼 Rasm", callback_data="image"),
            ],
            [
                InlineKeyboardButton(text="📋 Vazifalar", callback_data="tasks"),
                InlineKeyboardButton(text="🤖 Modellar", callback_data="models"),
            ],
            [
                InlineKeyboardButton(text="📊 Holat", callback_data="status"),
                InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="settings"),
            ],
            [InlineKeyboardButton(text="❓ Yordam", callback_data="help")],
        ]
    )


def back():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Bosh menyu", callback_data="home")]
        ]
    )


async def guard(message: Message):
    if allowed(message):
        return True
    await message.answer("⛔ Bu botdan foydalanish huquqi yo‘q.")
    return False


@dp.message(Command("start"))
async def start(message: Message):
    if not await guard(message):
        return
    name = message.from_user.first_name if message.from_user else "foydalanuvchi"
    await message.answer(
        f"Assalomu alaykum, <b>{name}</b>.\n\n"
        "AI Content Agent boshqaruv paneliga xush kelibsiz.",
        reply_markup=menu(),
    )


@dp.message(Command("help"))
async def help_command(message: Message):
    if not await guard(message):
        return
    await message.answer(
        "<b>AI Content Agent</b>\n\n"
        "/start — bosh menyu\n"
        "/task — erkin vazifa\n"
        "/post — post topshirig‘i\n"
        "/status — tizim holati\n"
        "/models — modellar\n\n"
        "Oddiy matn yuborsangiz ham vazifa sifatida queue'ga yoziladi.",
        reply_markup=back(),
    )


@dp.message(Command("task"))
async def task_command(message: Message):
    if not await guard(message):
        return
    text = (message.text or "").partition(" ")[2].strip()
    if not text:
        await message.answer(
            "<b>📋 Vazifa</b>\n\n"
            "Misol:\n"
            "<code>/task Bugungi AI yangiliklaridan 3 ta original post g‘oyasi top</code>"
        )
        return
    task_id = save_task(message.from_user.id, text)
    await message.answer(
        f"✅ Vazifa <b>#{task_id}</b> queue'ga qo‘shildi.",
        reply_markup=menu(),
    )


@dp.message(Command("post"))
async def post_command(message: Message):
    if not await guard(message):
        return
    text = (message.text or "").partition(" ")[2].strip()
    if not text:
        await message.answer(
            "<b>✍️ Post</b>\n\n"
            "Misol: <code>/post AI agentlar haqida post tayyorla</code>"
        )
        return
    task_id = save_task(message.from_user.id, "POST: " + text)
    await message.answer(f"✍️ Post vazifasi <b>#{task_id}</b> queue'ga qo‘shildi.")


@dp.message(Command("status"))
async def status_command(message: Message):
    if not await guard(message):
        return
    conn = db()
    count = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE status='queued'"
    ).fetchone()[0]
    conn.close()
    await message.answer(
        "<b>📊 Tizim holati</b>\n\n"
        "🟢 Telegram Bot: ONLINE\n"
        f"📋 Queue: <b>{count}</b>\n"
        f"🎯 Target: <code>{TARGET}</code>\n"
        f"💾 DB: <code>{DB_PATH}</code>",
        reply_markup=back(),
    )


@dp.message(F.text)
async def free_text(message: Message):
    if not await guard(message):
        return
    text = (message.text or "").strip()
    if not text:
        return
    task_id = save_task(message.from_user.id, text)
    await message.answer(
        f"🧠 Erkin vazifa <b>#{task_id}</b> qabul qilindi.",
        reply_markup=menu(),
    )


@dp.callback_query()
async def callbacks(call: CallbackQuery):
    await call.answer()
    if not call.message:
        return

    if call.data == "home":
        await call.message.edit_text(
            "🤖 <b>AI Content Agent</b>\n\nBo‘limni tanlang.",
            reply_markup=menu(),
        )
        return

    if call.data == "tasks":
        conn = db()
        rows = conn.execute(
            "SELECT id,text,status FROM tasks ORDER BY id DESC LIMIT 10"
        ).fetchall()
        conn.close()
        if rows:
            body = "\n\n".join(
                f"<b>#{row['id']}</b> · {row['status']}\n{row['text'][:350]}"
                for row in rows
            )
        else:
            body = "Hozircha vazifa yo‘q."
        await call.message.edit_text(
            "<b>📋 Vazifalar</b>\n\n" + body,
            reply_markup=back(),
        )
        return

    pages = {
        "post": "<b>✍️ Post yaratish</b>\n\nMavzuni keyingi xabarda yuboring.",
        "research": "<b>🔎 Research</b>\n\nResearch executor keyingi modulda ulanadi.",
        "ideas": "<b>💡 G‘oyalar</b>\n\nIdea generator keyingi modulda ulanadi.",
        "image": "<b>🖼 Rasm</b>\n\nImage agent keyingi modulda ulanadi.",
        "models": "<b>🤖 Modellar</b>\n\nOmniRoute model discovery keyingi modulda ulanadi.",
        "settings": f"<b>⚙️ Sozlamalar</b>\n\nTarget: <code>{TARGET}</code>\nDB: <code>{DB_PATH}</code>",
        "help": "<b>❓ Yordam</b>\n\n/start — menyu\n/task — vazifa\n/post — post\n/status — holat",
        "status": "🟢 Telegram Bot: ONLINE",
    }

    if call.data in pages:
        await call.message.edit_text(pages[call.data], reply_markup=back())


async def main():
    db().close()
    await bot.delete_webhook(drop_pending_updates=False)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
