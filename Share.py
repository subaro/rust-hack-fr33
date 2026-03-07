import sqlite3
import random
import time
from telegram import *
from telegram.ext import *

TOKEN = "8725586731:AAG1SCgp6tr3s1e-J6NfRZnnFwlUxQASFJE"
ADMIN_ID = 8522085072

conn = sqlite3.connect("bot.db",check_same_thread=False)
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY,balance REAL DEFAULT 0,ref INTEGER,banned INTEGER DEFAULT 0)")
cursor.execute("CREATE TABLE IF NOT EXISTS channels (id INTEGER PRIMARY KEY AUTOINCREMENT,owner INTEGER,username TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS bots (id INTEGER PRIMARY KEY AUTOINCREMENT,owner INTEGER,link TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS joins (user INTEGER,task INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS bot_verify (buyer INTEGER,owner INTEGER,bot_id INTEGER,time INTEGER,status TEXT)")
conn.commit()


def add_balance(user_id,amount):

    cursor.execute("UPDATE users SET balance=balance+? WHERE id=?",(amount,user_id))

    cursor.execute("SELECT ref FROM users WHERE id=?",(user_id,))
    ref=cursor.fetchone()

    if ref and ref[0]:
        ref_id=ref[0]
        bonus=amount*0.30
        cursor.execute("UPDATE users SET balance=balance+? WHERE id=?",(bonus,ref_id))

    conn.commit()


def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 القنوات",callback_data="channels")],
        [InlineKeyboardButton("🤖 البوتات",callback_data="bots")],
        [InlineKeyboardButton("💎 رصيدي",callback_data="balance")],
        [InlineKeyboardButton("🎁 الدعوات",callback_data="invite")]
    ])


def channel_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 تجميع روبلز",callback_data="collect_channels")],
        [InlineKeyboardButton("🚀 نشر قناة",callback_data="publish_channel")],
        [InlineKeyboardButton("⬅️ رجوع",callback_data="back")]
    ])


def bot_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 تجميع روبلز",callback_data="collect_bots")],
        [InlineKeyboardButton("🚀 نشر بوت",callback_data="publish_bot")],
        [InlineKeyboardButton("⬅️ رجوع",callback_data="back")]
    ])


async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user=update.effective_user.id
    ref=None

    if context.args:
        ref=int(context.args[0])
        if ref==user:
            ref=None

    cursor.execute("SELECT * FROM users WHERE id=?",(user,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users VALUES(?,?,?,?)",(user,0,ref,0))
        conn.commit()

    await update.message.reply_text(
        "اهلا بك في بوت الروبلز 💎",
        reply_markup=main_menu()
    )


async def menu(update:Update,context:ContextTypes.DEFAULT_TYPE):

    q=update.callback_query
    await q.answer()

    if q.data=="channels":
        await q.message.edit_text("قسم القنوات",reply_markup=channel_menu())

    elif q.data=="bots":
        await q.message.edit_text("قسم البوتات",reply_markup=bot_menu())

    elif q.data=="back":
        await q.message.edit_text("القائمة الرئيسية",reply_markup=main_menu())

    elif q.data=="balance":
        cursor.execute("SELECT balance FROM users WHERE id=?",(q.from_user.id,))
        bal=cursor.fetchone()[0]
        await q.message.reply_text(f"رصيدك {bal} روبل")

    elif q.data=="invite":
        link=f"https://t.me/{context.bot.username}?start={q.from_user.id}"
        await q.message.reply_text(
f"""🎁 نظام الدعوات

قم بدعوة أصدقائك للبوت واحصل على أرباح إضافية.

💰 ميزات الدعوة:
تحصل على 30٪ ربح إضافي من أرباح كل شخص تدعوه.

🔗 رابط الدعوة الخاص بك:
{link}"""
        )


async def collect_channels(update:Update,context:ContextTypes.DEFAULT_TYPE):

    q=update.callback_query
    user=q.from_user.id
    await q.answer()

    cursor.execute("""
    SELECT * FROM channels 
    WHERE owner!=? 
    AND id NOT IN (SELECT task FROM joins WHERE user=?)
    """,(user,user))

    data=cursor.fetchall()

    if not data:
        await q.message.reply_text("لا توجد قنوات حالياً للتجميع")
        return

    ch=random.choice(data)

    keyboard=InlineKeyboardMarkup([
        [InlineKeyboardButton("اشترك",url=f"https://t.me/{ch[2].replace('@','')}")],
        [InlineKeyboardButton("تحقق",callback_data=f"check_{ch[0]}")]
    ])

    await q.message.reply_text("اشترك ثم تحقق",reply_markup=keyboard)


async def collect_bots(update:Update,context:ContextTypes.DEFAULT_TYPE):

    q=update.callback_query
    user=q.from_user.id
    await q.answer()

    cursor.execute("SELECT * FROM bots WHERE owner!=?",(user,))
    data=cursor.fetchall()

    if not data:
        await q.message.reply_text("لا توجد بوتات")
        return

    bot=random.choice(data)

    keyboard=InlineKeyboardMarkup([
        [InlineKeyboardButton("فتح البوت",url=bot[2])],
        [InlineKeyboardButton("تحقق",callback_data=f"botcheck_{bot[0]}")]
    ])

    await q.message.reply_text("افتح البوت ثم اضغط تحقق",reply_markup=keyboard)


async def check(update:Update,context:ContextTypes.DEFAULT_TYPE):

    q=update.callback_query
    user=q.from_user.id
    ch_id=int(q.data.split("_")[1])

    cursor.execute("SELECT owner,username FROM channels WHERE id=?",(ch_id,))
    data=cursor.fetchone()

    if not data:
        await q.answer("القناة غير موجودة",show_alert=True)
        return

    owner,username=data

    try:
        member=await context.bot.get_chat_member(username,user)

        if member.status in ["member","administrator","creator"]:

            cursor.execute("SELECT * FROM joins WHERE user=? AND task=?",(user,ch_id))
            if cursor.fetchone():
                await q.answer("تم التنفيذ مسبقا")
                return

            cursor.execute("INSERT INTO joins VALUES(?,?)",(user,ch_id))
            add_balance(user,0.5)

            await q.message.reply_text("تم إضافة 0.5 روبل 💰")

        else:
            await q.answer("لم تشترك",show_alert=True)

    except:
        await q.answer("تعذر التحقق من الاشتراك",show_alert=True)


async def botcheck(update:Update,context:ContextTypes.DEFAULT_TYPE):

    q=update.callback_query
    user=q.from_user.id
    bot_id=int(q.data.split("_")[1])

    cursor.execute("SELECT owner FROM bots WHERE id=?",(bot_id,))
    owner=cursor.fetchone()[0]

    cursor.execute("INSERT INTO bot_verify VALUES(?,?,?,?,?)",(user,owner,bot_id,int(time.time()),"pending"))
    conn.commit()

    keyboard=InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأكيد",callback_data=f"confirm_{user}_{bot_id}")],
        [InlineKeyboardButton("❌ لم يتم الاشتراك",callback_data=f"deny_{user}_{bot_id}")]
    ])

    await context.bot.send_message(
        owner,
        "🔔 قام احدهم بالاشتراك في رابط البوت الخاص بك\nهل تم الاشتراك؟",
        reply_markup=keyboard
    )

    await q.message.reply_text("تم ارسال طلب التحقق لصاحب البوت")


async def confirm(update:Update,context:ContextTypes.DEFAULT_TYPE):

    q=update.callback_query
    await q.answer()

    data=q.data.split("_")
    buyer=int(data[1])
    bot_id=int(data[2])

    cursor.execute("UPDATE bot_verify SET status='done' WHERE buyer=? AND bot_id=?",(buyer,bot_id))
    add_balance(buyer,0.2)
    conn.commit()

    try:
        await context.bot.send_message(
            buyer,
            "✅ تم تأكيد الاشتراك وتم إضافة 0.2 روبلز إلى حسابك"
        )
    except:
        pass

    await q.message.edit_text("✅ تم تأكيد الاشتراك وإضافة المكافأة")


async def deny(update:Update,context:ContextTypes.DEFAULT_TYPE):

    q=update.callback_query
    await q.answer()

    data=q.data.split("_")
    buyer=int(data[1])
    bot_id=int(data[2])

    cursor.execute("UPDATE bot_verify SET status='denied' WHERE buyer=? AND bot_id=?",(buyer,bot_id))
    conn.commit()

    try:
        await context.bot.send_message(
            buyer,
            "❌ فشل التحقق من الاشتراك قام المستخدم بالرفض"
        )
    except:
        pass

    await q.message.edit_text("❌ تم رفض الاشتراك")


async def publish_channel(update:Update,context:ContextTypes.DEFAULT_TYPE):
    context.user_data["add_channel"]=True
    context.user_data["add_bot"]=False
    await update.callback_query.message.reply_text(
"""📢 ارسل رابط القناة

⚠️ يجب إضافة البوت أدمن في القناة قبل النشر

مثال
https://t.me/channelname"""
)


async def publish_bot(update:Update,context:ContextTypes.DEFAULT_TYPE):
    context.user_data["add_bot"]=True
    context.user_data["add_channel"]=False
    await update.callback_query.message.reply_text("ارسل رابط البوت")


async def text(update:Update,context:ContextTypes.DEFAULT_TYPE):

    user=update.message.from_user.id
    msg=update.message.text.strip()

    cursor.execute("SELECT balance FROM users WHERE id=?",(user,))
    bal=cursor.fetchone()[0]

    if context.user_data.get("add_channel"):

        if bal<1:
            await update.message.reply_text("❌ تحتاج 1 روبل للنشر")
            return

        if not msg.startswith("https://t.me/"):
            await update.message.reply_text("❌ ارسل رابط قناة صحيح")
            return

        username=msg.replace("https://t.me/","")

        if "?" in username:
            username=username.split("?")[0]

        if username.lower().endswith("bot"):
            await update.message.reply_text("❌ هذا رابط بوت وليس قناة")
            return

        username="@"+username

        try:
            bot_member = await context.bot.get_chat_member(username, context.bot.id)

            if bot_member.status not in ["administrator","creator"]:
                await update.message.reply_text("❌ يجب إضافة البوت أدمن في القناة أولاً")
                return

        except:
            await update.message.reply_text("❌ تأكد من إضافة البوت أدمن ثم أرسل الرابط مرة أخرى")
            return

        cursor.execute("UPDATE users SET balance=balance-1 WHERE id=?",(user,))
        cursor.execute("INSERT INTO channels(owner,username) VALUES(?,?)",(user,username))
        conn.commit()

        context.user_data["add_channel"]=False
        await update.message.reply_text("✅ تم نشر القناة")

    elif context.user_data.get("add_bot"):

        if bal<1:
            await update.message.reply_text("❌ تحتاج 1 روبل للنشر")
            return

        if not msg.startswith("https://t.me/"):
            await update.message.reply_text("❌ مسموح فقط روابط بوتات تيليجرام")
            return

        username=msg.replace("https://t.me/","")

        if "?" in username:
            username=username.split("?")[0]

        if not username.lower().endswith("bot"):
            await update.message.reply_text("❌ هذا رابط قناة وليس بوت")
            return

        cursor.execute("UPDATE users SET balance=balance-1 WHERE id=?",(user,))
        cursor.execute("INSERT INTO bots(owner,link) VALUES(?,?)",(user,msg))
        conn.commit()

        context.user_data["add_bot"]=False
        await update.message.reply_text("✅ تم نشر البوت")


async def add(update:Update,context:ContextTypes.DEFAULT_TYPE):

    if update.message.from_user.id!=ADMIN_ID:
        return

    uid=int(context.args[0])
    amount=float(context.args[1])

    cursor.execute("UPDATE users SET balance=balance+? WHERE id=?",(amount,uid))
    conn.commit()

    await update.message.reply_text("تمت الاضافة")


async def remove(update:Update,context:ContextTypes.DEFAULT_TYPE):

    if update.message.from_user.id!=ADMIN_ID:
        return

    uid=int(context.args[0])
    amount=float(context.args[1])

    cursor.execute("UPDATE users SET balance=balance-? WHERE id=?",(amount,uid))
    conn.commit()

    await update.message.reply_text("تم الخصم")


async def stats(update:Update,context:ContextTypes.DEFAULT_TYPE):

    if update.message.from_user.id!=ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*) FROM users")
    users=cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM channels")
    channels=cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM bots")
    bots=cursor.fetchone()[0]

    await update.message.reply_text(
        f"المستخدمين: {users}\nالقنوات: {channels}\nالبوتات: {bots}"
    )


app=ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start",start))
app.add_handler(CommandHandler("add",add))
app.add_handler(CommandHandler("remove",remove))
app.add_handler(CommandHandler("stats",stats))

app.add_handler(CallbackQueryHandler(collect_channels,pattern="collect_channels"))
app.add_handler(CallbackQueryHandler(collect_bots,pattern="collect_bots"))
app.add_handler(CallbackQueryHandler(check,pattern="check_"))
app.add_handler(CallbackQueryHandler(botcheck,pattern="botcheck_"))
app.add_handler(CallbackQueryHandler(confirm,pattern="confirm_"))
app.add_handler(CallbackQueryHandler(deny,pattern="deny_"))
app.add_handler(CallbackQueryHandler(publish_channel,pattern="publish_channel"))
app.add_handler(CallbackQueryHandler(publish_bot,pattern="publish_bot"))
app.add_handler(CallbackQueryHandler(menu))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,text))

print("BOT RUNNING")
app.run_polling()
