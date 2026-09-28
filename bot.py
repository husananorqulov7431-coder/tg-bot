import asyncio
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo
from dotenv import load_dotenv

ROOT=Path(__file__).resolve().parent
load_dotenv(ROOT/".env")
DATA_DIR=Path(os.getenv("DATA_DIR", str(ROOT/"data")))
DB_PATH=DATA_DIR/"bot.sqlite3"
UPLOAD_DIR=DATA_DIR/"uploads"
TOKEN=os.getenv("TELEGRAM_BOT_TOKEN","").strip()
TARGET=os.getenv("TELEGRAM_TARGET","@teleposttestuz").strip()
MINIAPP_URL=os.getenv("MINIAPP_URL","").strip()
_raw_ids=os.getenv("ALLOWED_USER_IDS","").strip()
ALLOWED_USER_IDS={int(x.strip()) for x in _raw_ids.split(",") if x.strip().isdigit()}
if not TOKEN: raise RuntimeError("TELEGRAM_BOT_TOKEN is missing")
DATA_DIR.mkdir(parents=True,exist_ok=True); UPLOAD_DIR.mkdir(parents=True,exist_ok=True)
logging.basicConfig(level=os.getenv("LOG_LEVEL","INFO"),format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
log=logging.getLogger("telegram-agent")
bot=Bot(TOKEN,default=DefaultBotProperties(parse_mode=ParseMode.HTML)); dp=Dispatcher()

def now_iso(): return datetime.now(timezone.utc).isoformat()
def db():
    c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row
    c.execute("CREATE TABLE IF NOT EXISTS users (telegram_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, last_seen TEXT NOT NULL)")
    c.execute("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id INTEGER NOT NULL, text TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'queued', created_at TEXT NOT NULL)")
    c.commit(); return c
def allowed(uid:Optional[int]): return not ALLOWED_USER_IDS or (uid is not None and uid in ALLOWED_USER_IDS)
def remember(m):
    if not m.from_user:return
    c=db(); c.execute("""INSERT INTO users VALUES (?,?,?,?) ON CONFLICT(telegram_id) DO UPDATE SET username=excluded.username, first_name=excluded.first_name, last_seen=excluded.last_seen""",(m.from_user.id,m.from_user.username,m.from_user.first_name,now_iso())); c.commit(); c.close()
def save_task(uid,text):
    c=db(); cur=c.execute("INSERT INTO tasks(telegram_id,text,status,created_at) VALUES(?,?,?,?)",(uid,text,"queued",now_iso())); tid=int(cur.lastrowid); c.commit(); c.close(); return tid
def kb():
    rows=[
      [InlineKeyboardButton(text="✍️ Post yaratish",callback_data="post:new"),InlineKeyboardButton(text="🔎 Research",callback_data="research")],
      [InlineKeyboardButton(text="💡 G‘oyalar",callback_data="ideas"),InlineKeyboardButton(text="🖼 Rasm",callback_data="image")],
      [InlineKeyboardButton(text="📋 Vazifalar",callback_data="tasks"),InlineKeyboardButton(text="📝 Draftlar",callback_data="drafts")],
      [InlineKeyboardButton(text="🤖 Modellar",callback_data="models"),InlineKeyboardButton(text="⚙️ Sozlamalar",callback_data="settings")],
      [InlineKeyboardButton(text="📊 Holat",callback_data="status"),InlineKeyboardButton(text="❓ Yordam",callback_data="help")]]
    if MINIAPP_URL.startswith(("https://","http://")): rows.append([InlineKeyboardButton(text="🖥 AI Control Panel",web_app=WebAppInfo(url=MINIAPP_URL))])
    return InlineKeyboardMarkup(inline_keyboard=rows)
def back(): return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Bosh menyu",callback_data="home")]])
async def guard(m):
    if allowed(m.from_user.id if m.from_user else None): return True
    await m.answer("⛔ Bu botdan foydalanish huquqi yo‘q."); return False

@dp.message(Command("start"))
async def start(m):
    if not await guard(m): return
    remember(m); name=m.from_user.first_name if m.from_user else "foydalanuvchi"
    await m.answer(f"Assalomu alaykum, <b>{name}</b>.\n\nAI Content Agent boshqaruv paneliga xush kelibsiz.",reply_markup=kb())

@dp.message(Command("help"))
async def help_cmd(m):
    if not await guard(m): return
    remember(m)
    await m.answer("<b>AI Content Agent</b>\n\n/start — bosh menyu\n/help — yordam\n/task — erkin vazifa\n/post — post topshirig‘i\n/drafts — queue\n/status — tizim holati\n/models — modellar\n\nOddiy matn yuborsangiz, u ham erkin vazifa sifatida queue'ga yoziladi.",reply_markup=back())

@dp.message(Command("status"))
async def status(m):
    if not await guard(m): return
    remember(m); c=db(); q=c.execute("SELECT COUNT(*) FROM tasks WHERE status='queued'").fetchone()[0]; c.close()
    await m.answer(f"<b>📊 Tizim holati</b>\n\n🟢 Telegram Bot: ONLINE\n📋 Queue: <b>{q}</b>\n🎯 Target: <code>{TARGET}</code>\n💾 DB: <code>{DB_PATH}</code>",reply_markup=back())

@dp.message(Command("models"))
async def models(m):
    if not await guard(m): return
    remember(m)
    await m.answer("<b>🤖 Modellar</b>\n\nModel registry interfeysi tayyor. OmniRoute discovery keyingi modulda ulanadi.",reply_markup=back())

@dp.message(Command("drafts"))
async def drafts(m):
    if not await guard(m): return
    remember(m); await show_queue(m.chat.id)

@dp.message(Command("task"))
async def task(m):
    if not await guard(m): return
    remember(m); text=(m.text or "").partition(" ")[2].strip()
    if not text:
        await m.answer("<b>📋 Vazifa</b>\n\nMasalan:\n<code>/task Bugungi AI yangiliklaridan 3 ta original post g‘oyasi top</code>"); return
    tid=save_task(m.from_user.id,text); await m.answer(f"✅ Vazifa qabul qilindi.\n\nID: <b>#{tid}</b>\nStatus: <b>queued</b>",reply_markup=kb())

@dp.message(Command("post"))
async def post(m):
    if not await guard(m): return
    remember(m); text=(m.text or "").partition(" ")[2].strip()
    if not text:
        await m.answer("<b>✍️ Yangi post</b>\n\nMavzuni yuboring yoki /post dan keyin yozing.",reply_markup=back()); return
    tid=save_task(m.from_user.id,"POST: "+text); await m.answer(f"✍️ Post topshirig‘i qabul qilindi: <b>#{tid}</b>\nStatus: <b>queued</b>")

@dp.message(F.document)
async def document(m):
    if not await guard(m): return
    remember(m); doc=m.document; filename=Path(doc.file_name or "file.bin").name; dest=UPLOAD_DIR/f"{m.message_id}_{filename}"
    f=await bot.get_file(doc.file_id); await bot.download_file(f.file_path,dest)
    await m.answer(f"📎 <b>{filename}</b> saqlandi.\n<code>{dest}</code>")

@dp.message(F.text)
async def free_text(m):
    if not await guard(m): return
    remember(m); text=(m.text or "").strip()
    if not text:return
    tid=save_task(m.from_user.id,text); await m.answer(f"🧠 <b>Erkin vazifa qabul qilindi</b>\n\nID: <b>#{tid}</b>\nStatus: <b>queued</b>",reply_markup=kb())

async def show_queue(chat_id):
    c=db(); rows=c.execute("SELECT id,text,status,created_at FROM tasks ORDER BY id DESC LIMIT 10").fetchall(); c.close()
    body="<b>📋 Vazifalar</b>\n\n"+("Hozircha vazifa yo‘q." if not rows else "\n\n".join(f"<b>#{r['id']}</b> · {r['status']}\n{r['text'][:350]}" for r in rows))
    await bot.send_message(chat_id,body,reply_markup=back())

@dp.callback_query(F.data=="home")
async def home(c:CallbackQuery):
    await c.answer()
    if c.message: await c.message.edit_text("🤖 <b>AI Content Agent</b>\n\nKerakli bo‘limni tanlang.",reply_markup=kb())
@dp.callback_query(F.data=="help")
async def cb_help(c):
    await c.answer()
    if c.message: await c.message.edit_text("<b>Yordam</b>\n\nPost, research, task, model va status bo‘limlari orqali boshqariladi.",reply_markup=back())
@dp.callback_query(F.data=="status")
async def cb_status(c):
    await c.answer()
    if not c.message:return
    conn=db(); q=conn.execute("SELECT COUNT(*) FROM tasks WHERE status='queued'").fetchone()[0]; conn.close()
    await c.message.edit_text(f"<b>📊 Tizim holati</b>\n\n🟢 Telegram Bot: ONLINE\n📋 Queue: {q}\n💾 DB: <code>{DB_PATH}</code>",reply_markup=back())
@dp.callback_query(F.data=="tasks")
async def cb_tasks(c):
    await c.answer()
    if c.message: await show_queue(c.message.chat.id)
@dp.callback_query(F.data=="drafts")
async def cb_drafts(c):
    await c.answer()
    if c.message: await show_queue(c.message.chat.id)
@dp.callback_query(F.data=="post:new")
async def cb_post(c):
    await c.answer()
    if c.message: await c.message.edit_text("<b>✍️ Yangi post</b>\n\nMavzuni keyingi xabarda yuboring.",reply_markup=back())
@dp.callback_query(F.data=="research")
async def cb_research(c):
    await c.answer()
    if c.message: await c.message.edit_text("<b>🔎 Research</b>\n\nResearch executor keyingi modulda ulanadi.",reply_markup=back())
@dp.callback_query(F.data=="ideas")
async def cb_ideas(c):
    await c.answer()
    if c.message: await c.message.edit_text("<b>💡 G‘oyalar</b>\n\nIdea generator keyingi AI modulda ulanadi.",reply_markup=back())
@dp.callback_query(F.data=="image")
async def cb_image(c):
    await c.answer()
    if c.message: await c.message.edit_text("<b>🖼 Rasm</b>\n\nImage agent keyingi modulda ulanadi.",reply_markup=back())
@dp.callback_query(F.data=="models")
async def cb_models(c):
    await c.answer()
    if c.message: await c.message.edit_text("<b>🤖 Modellar</b>\n\nOmniRoute model discovery keyingi modulda ulanadi.",reply_markup=back())
@dp.callback_query(F.data=="settings")
async def cb_settings(c):
    await c.answer()
    if c.message: await c.message.edit_text(f"<b>⚙️ Sozlamalar</b>\n\nTarget: <code>{TARGET}</code>\nDatabase: <code>{DB_PATH}</code>\nMini App: {'ON' if MINIAPP_URL else 'OFF'}",reply_markup=back())
@dp.callback_query(F.data=="models:refresh")
async def cb_models_refresh(c): await c.answer("Model registry hali ulanmagan",show_alert=True)

async def main():
    log.info("Starting Telegram Agent Core"); db().close(); await bot.delete_webhook(drop_pending_updates=False); await dp.start_polling(bot)

if __name__=="__main__": asyncio.run(main())
