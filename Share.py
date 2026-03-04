import os import sqlite3 from datetime import datetime, timedelta from
flask import Flask, request from telegram import Update,
InlineKeyboardMarkup, InlineKeyboardButton from telegram.ext import (
ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes,
)

================= CONFIG =================

TOKEN = os.getenv(“TOKEN”) ADMIN_ID = int(os.getenv(“ADMIN_ID”))

================= DATABASE =================

conn = sqlite3.connect(“ruble_system.db”, check_same_thread=False)
cursor = conn.cursor()

cursor.execute(“““CREATE TABLE IF NOT EXISTS users( user_id INTEGER
PRIMARY KEY, balance REAL DEFAULT 0, banned INTEGER DEFAULT 0,
bot_rejects INTEGER DEFAULT 0 )”““)

cursor.execute(“““CREATE TABLE IF NOT EXISTS channels( id INTEGER
PRIMARY KEY AUTOINCREMENT, owner_id INTEGER, username TEXT, priority
INTEGER DEFAULT 0, reward REAL DEFAULT 0.2 )”““)

cursor.execute(“““CREATE TABLE IF NOT EXISTS bots( id INTEGER PRIMARY
KEY AUTOINCREMENT, owner_id INTEGER, username TEXT, priority INTEGER
DEFAULT 0, reward REAL DEFAULT 0.2 )”““)

cursor.execute(“““CREATE TABLE IF NOT EXISTS subscriptions( user_id
INTEGER, channel_id INTEGER )”““)

cursor.execute(“““CREATE TABLE IF NOT EXISTS bot_requests( id INTEGER
PRIMARY KEY AUTOINCREMENT, subscriber_id INTEGER, bot_id INTEGER, status
TEXT, created_at TEXT )”““)

conn.commit()

================= TELEGRAM APP =================

application = ApplicationBuilder().token(TOKEN).build()

def is_admin(user_id): return user_id == ADMIN_ID

def main_menu(): return InlineKeyboardMarkup([ [InlineKeyboardButton(“📢
تبادل قنوات”, callback_data=“channels”)], [InlineKeyboardButton(“🤖
تبادل بوتات”, callback_data=“bots”)], [InlineKeyboardButton(“💎 رصيدي”,
callback_data=“balance”)], [InlineKeyboardButton(“🏆 أعلى 10”,
callback_data=“top”)] ])

================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
user_id = update.effective_user.id cursor.execute(“INSERT OR IGNORE INTO
users(user_id) VALUES(?)”,(user_id,)) conn.commit() await
update.message.reply_text( “✨ مرحباً بك في نظام روبل 💎”,
reply_markup=main_menu() )

================= BALANCE =================

async def balance(update:Update,context:ContextTypes.DEFAULT_TYPE):
query=update.callback_query cursor.execute(“SELECT balance FROM users
WHERE user_id=?”,(query.from_user.id,)) bal=cursor.fetchone()[0] await
query.answer() await query.message.reply_text(f”💎 رصيدك: {bal:.2f}
روبل”)

================= TOP =================

async def top_users(update:Update,context:ContextTypes.DEFAULT_TYPE):
query=update.callback_query cursor.execute(“SELECT user_id,balance FROM
users ORDER BY balance DESC LIMIT 10”) data=cursor.fetchall() text=“🏆
أعلى 10 مستخدمين:” for i,row in enumerate(data,1): text+=f”{i}.
{row[0]} - {row[1]:.2f} روبل” await query.answer() await
query.message.reply_text(text)

================= AUTO APPROVE =================

async def auto_approve(context:ContextTypes.DEFAULT_TYPE):
cursor.execute(“SELECT id,subscriber_id,bot_id,created_at FROM
bot_requests WHERE status=‘pending’”) rows=cursor.fetchall() for row in
rows: created=datetime.fromisoformat(row[3]) if
datetime.now()-created>timedelta(hours=6): cursor.execute(“SELECT reward
FROM bots WHERE id=?”,(row[2],)) reward=cursor.fetchone()[0]
cursor.execute(“UPDATE users SET balance=balance+? WHERE
user_id=?”,(reward,row[1])) cursor.execute(“UPDATE bot_requests SET
status=‘auto_approved’ WHERE id=?”,(row[0],)) conn.commit() await
context.bot.send_message(row[1],f”⏳ تم التحقق تلقائياً +{reward} روبل
💎“)

================= HANDLERS =================

application.add_handler(CommandHandler(“start”,start))
application.add_handler(CallbackQueryHandler(balance,pattern=“balance”))
application.add_handler(CallbackQueryHandler(top_users,pattern=“top”))

application.job_queue.run_repeating(auto_approve,interval=600,first=10)

================= FLASK =================

app = Flask(name)

@app.route(“/”, methods=[“POST”]) async def webhook(): update =
Update.de_json(request.get_json(force=True), application.bot) await
application.process_update(update) return “OK”

@app.route(“/”, methods=[“GET”]) def home(): return “Bot is running 🚀”

@app.before_first_request async def startup(): await
application.initialize() await application.start()

if name == “main”: app.run()
