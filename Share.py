import os
import sqlite3
from flask import Flask, request
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ================= CONFIG =================

TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")

# ================= DATABASE =================

conn = sqlite3.connect("ruble_pro.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS users(
user_id INTEGER PRIMARY KEY,
balance REAL DEFAULT 0,
inviter_id INTEGER,
referrals INTEGER DEFAULT 0,
level INTEGER DEFAULT 1,
banned INTEGER DEFAULT 0
)""")

conn.commit()

# ================= LEVEL SYSTEM =================

LEVELS = {
    1: ("🥉 Bronze", 0.2),
    2: ("🥈 Silver", 0.3),
    3: ("🥇 Gold", 0.4),
    4: ("💎 Platinum", 0.5),
    5: ("👑 Elite", 0.6),
}

def get_level_bonus(level):
    return LEVELS.get(level, LEVELS[5])[1]

def get_level_name(level):
    return LEVELS.get(level, LEVELS[5])[0]

def check_level_upgrade(user_id):
    cursor.execute("SELECT referrals, level FROM users WHERE user_id=?", (user_id,))
    referrals, level = cursor.fetchone()
    new_level = (referrals // 5) + 1
    if new_level > level and new_level <= 5:
        cursor.execute("UPDATE users SET level=? WHERE user_id=?", (new_level, user_id))
        conn.commit()
        return True
    return False

# ================= TELEGRAM =================

application = ApplicationBuilder().token(TOKEN).build()

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 حسابي", callback_data="profile")],
        [InlineKeyboardButton("🔗 رابط الدعوة", callback_data="referral")]
    ])

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    inviter_id = None
    if context.args:
        try:
            inviter_id = int(context.args[0])
            if inviter_id == user_id:
                inviter_id = None
        except:
            inviter_id = None

    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    exists = cursor.fetchone()

    if not exists:
        cursor.execute(
            "INSERT INTO users(user_id, inviter_id) VALUES(?,?)",
            (user_id, inviter_id),
        )
        if inviter_id:
            cursor.execute("UPDATE users SET referrals=referrals+1 WHERE user_id=?", (inviter_id,))
        conn.commit()

    await update.message.reply_text(
        "✨ أهلاً بك في Ruble Exchange PRO 💎",
        reply_markup=main_menu()
    )

# ================= PROFILE =================

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    cursor.execute("SELECT balance, referrals, level FROM users WHERE user_id=?", (user_id,))
    data = cursor.fetchone()

    balance, referrals, level = data
    level_name = get_level_name(level)
    bonus = get_level_bonus(level)

    text = f"""
━━━━━━━━━━━━━━━━━━
💎 Ruble Exchange PRO

👤 ID: {user_id}
🏆 المستوى: {level_name}
👥 الدعوات: {referrals}
💰 الرصيد: {balance:.2f} روبل
🎁 مكافأة الاشتراك: {bonus} روبل
━━━━━━━━━━━━━━━━━━
"""

    await query.answer()
    await query.message.reply_text(text)

# ================= REFERRAL =================

async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    link = f"https://t.me/{context.bot.username}?start={user_id}"

    await query.answer()
    await query.message.reply_text(
        f"🔗 رابط الدعوة الخاص بك:\n\n{link}\n\n"
        "💰 تأخذ 30% من أرباح أي شخص تدعوه!"
    )

# ================= REWARD FUNCTION =================

def add_balance(user_id, amount):
    cursor.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amount, user_id))

    cursor.execute("SELECT inviter_id FROM users WHERE user_id=?", (user_id,))
    inviter = cursor.fetchone()[0]

    if inviter:
        referral_bonus = amount * 0.30
        cursor.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (referral_bonus, inviter))

    conn.commit()

# ================= HANDLERS =================

application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(profile, pattern="profile"))
application.add_handler(CallbackQueryHandler(referral, pattern="referral"))

# ================= FLASK =================

app = Flask(__name__)

@app.route("/", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return "OK"

@app.route("/", methods=["GET"])
def home():
    return "Ruble Exchange PRO Running 🚀"

@app.before_first_request
async def startup():
    await application.initialize()
    await application.start()
    await application.bot.set_webhook(f"{RENDER_URL}/")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
