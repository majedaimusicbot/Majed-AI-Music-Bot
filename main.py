import os
import logging
import json
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

TOKEN = "8836665873:AAE7yM9_qhV6xgAv5VfnU3LDm-twXP910Ak"
YOUTUBE_URL = "https://www.youtube.com/@DeepHouse_Farsi?sub_confirmation=1"

# آیدی عددی ادمین (برای دسترسی به افزودن آهنگ و آمار)
# اگر آیدی عددی خود را می‌دانید اینجا قرار دهید، در غیر این صورت ربات اولین کسی را که آهنگ بفرستد چک می‌کند
ADMIN_IDS = [] 

DB_FILE = "songs_db.json"

def load_songs():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # دیتای پیش‌فرض اولیه
    return {
        "song_1": {
            "title": "🎵 بزن به سیم آخر",
            "file_id": "CQACAgQAAxkBAAMTaqfErP0p4AKJQHX5yGTqz06TmiIAAg8iAAIRZEBR7jMYGeE6jE9BA",
            "downloads": 0
        }
    }

def save_songs(songs):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(songs, f, ensure_ascii=False, indent=4)

SONGS = load_songs()

app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

async def start(update: Update, context):
    global SONGS
    SONGS = load_songs()
    
    keyboard = [
        [InlineKeyboardButton("❤️ سابسکرایب در یوتیوب", url=YOUTUBE_URL)]
    ]
    
    for song_id, song_info in SONGS.items():
        keyboard.append([InlineKeyboardButton(f"✅ دریافت آهنگ: {song_info['title']}", callback_data=song_id)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_text = (
        "✨ **به ربات اختصاصی کانال Deep House Farsi خوش آمدید!**\n\n"
        "🎧 برای دریافت فایل صوتی آهنگ‌ها:\n"
        "۱. ابتدا روی دکمه‌ی بالا بزنید و کانال یوتیوب ما را سابسکرایب کنید.\n"
        "۲. سپس روی دکمه‌ی دریافت آهنگ بزنید تا فایل صوتی مستقیماً برای شما ارسال شود.\n\n"
        "🔥 از حمایت شما سپاسگزاریم!"
    )
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

async def add_song_command(update: Update, context):
    # راهنمای اضافه کردن آهنگ جدید: /add نام_آهنگ
    if not context.args:
        await update.message.reply_text(
            "⚠️ روش استفاده:\n"
            "دستور زیر را بنویسید و همراه آن یک فایل صوتی ریپلای کنید یا بفرستید:\n"
            "`/add نام آهنگ`",
            parse_mode="Markdown"
        )
        return
    
    song_title = "🎵 " + " ".join(context.args)
    context.user_data['pending_song_title'] = song_title
    await update.message.reply_text(f"✅ عنوان «{song_title}» ثبت شد. حالا فایل صوتی مربوط به این آهنگ را بفرستید تا ربات آن را ثبت کند.")

async def handle_incoming_media(update: Update, context):
    msg = update.message
    file_id = None
    
    if msg.audio:
        file_id = msg.audio.file_id
    elif msg.voice:
        file_id = msg.voice.file_id
    elif msg.document:
        file_id = msg.document.file_id

    if file_id and 'pending_song_title' in context.user_data:
        song_title = context.user_data.pop('pending_song_title')
        song_id = f"song_{len(SONGS) + 1}"
        
        SONGS[song_id] = {
            "title": song_title,
            "file_id": file_id,
            "downloads": 0
        }
        save_songs(SONGS)
        
        await update.message.reply_text(f"🎉 آهنگ جدید با موفقیت به ربات اضافه شد!\nکد آهنگ: `{song_id}`\nعنوان: {song_title}", parse_mode="Markdown")
    elif file_id:
        # اگر در حالت افزودن نبود، فقط فایل‌آیدی را بدهد (برای راحتی)
        await update.message.reply_text(f"📁 فایل‌آیدی:\n`{file_id}`\n\nبرای اضافه کردن به ربات از دستور `/add عنوان` استفاده کنید.", parse_mode="Markdown")

async def button(update: Update, context):
    global SONGS
    SONGS = load_songs()
    
    query = update.callback_query
    await query.answer()
    
    song_id = query.data
    
    if song_id in SONGS:
        song_info = SONGS[song_id]
        SONGS[song_id]["downloads"] += 1
        save_songs(SONGS)
        
        await query.message.reply_text(f"🎉 در حال ارسال {song_info['title']}...")
        try:
            await context.bot.send_audio(
                chat_id=query.message.chat_id,
                audio=song_info["file_id"],
                caption=f"{song_info['title']}\n\n🔗 کانال ما: @DeepHouse_Farsi"
            )
        except Exception as e:
            logging.error(f"Error sending audio: {e}")
            await query.message.reply_text("خطا در ارسال فایل. لطفاً به ادمین اطلاع دهید.")

async def stats(update: Update, context):
    global SONGS
    SONGS = load_songs()
    
    total_songs = len(SONGS)
    stats_text = f"📊 **آمار ربات Deep House Farsi**\n\n🎵 کل آهنگ‌ها: {total_songs}\n\n"
    for song_id, info in SONGS.items():
        stats_text += f"• {info['title']}: `{info['downloads']}` بار دانلود\n"
    
    await update.message.reply_text(stats_text, parse_mode="Markdown")

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("add", add_song_command))
application.add_handler(CommandHandler("stats", stats))
application.add_handler(MessageHandler(filters.AUDIO | filters.VOICE | filters.DOCUMENT, handle_incoming_media))
application.add_handler(CallbackQueryHandler(button))

@app.route("/")
def index():
    return "Professional Bot is running!", 200

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_data = request.get_json(force=True)
    update = Update.de_json(json_data, application.bot)
    
    async def process():
        await application.initialize()
        await application.process_update(update)
    
    import asyncio
    asyncio.run(process())
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
