import os
import logging
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

TOKEN = "8836665873:AAE7yM9_qhV6xgAv5VfnU3LDm-twXP910Ak"
YOUTUBE_URL = "https://www.youtube.com/@DeepHouse_Farsi?sub_confirmation=1"

SONGS = {
    "song_1": {
        "title": "🎵 بزن به سیم آخر",
        "file_id": "CQACAgQAAxkBAAMTaqfErP0p4AKJQHX5yGTqz06TmiIAAg8iAAIRZEBR7jMYGeE6jE9BA",
        "downloads": 0
    }
}

app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

async def start(update: Update, context):
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
        "۲. سپس روی دکمه‌ی دریافت آهنگ بزنید تا پیام بررسی برای شما ارسال شود.\n\n"
        "🔥 از حمایت شما سپاسگزاریم!"
    )
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

async def get_file_id(update: Update, context):
    msg = update.message
    file_id = None
    file_type = "نامشخص"
    
    if msg.audio:
        file_id = msg.audio.file_id
        file_type = "Audio"
    elif msg.voice:
        file_id = msg.voice.file_id
        file_type = "Voice"
    elif msg.document:
        file_id = msg.document.file_id
        file_type = "Document"
        
    if file_id:
        await update.message.reply_text(
            f"📁 **فایل‌آیدی این {file_type}:**\n`{file_id}`\n\n"
            f"برای اضافه کردن آهنگ جدید، می‌توانید از این فایل‌آیدی استفاده کنید.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("لطفاً یک فایل صوتی معتبر بفرستید.")

async def button(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data in SONGS:
        song_info = SONGS[data]
        keyboard = [
            [InlineKeyboardButton("❤️ برو به کانال و سابسکرایب کن", url=YOUTUBE_URL)],
            [InlineKeyboardButton("✅ سابسکرایب کردم، دریافت آهنگ", callback_data=f"download_{data}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            f"⚠️ **توجه:** شما هنوز کانال یوتیوب ما را سابسکرایب نکرده‌اید!\n\n"
            f"برای دریافت آهنگ **{song_info['title']}**، ابتدا روی لینک زیر بزنید و سابسکرایب کنید، سپس روی دکمه‌ی تأیید بزنید.",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    elif data.startswith("download_"):
        song_id = data.replace("download_", "")
        if song_id in SONGS:
            song_info = SONGS[song_id]
            SONGS[song_id]["downloads"] += 1
            
            await query.message.reply_text(f"🎉 ممنون از حمایت شما! در حال ارسال {song_info['title']}...")
            try:
                await context.bot.send_audio(
                    chat_id=query.message.chat_id,
                    audio=song_info["file_id"],
                    caption=f"{song_info['title']}\n\n🔗 کانال ما: @DeepHouse_Farsi"
                )
            except Exception as e:
                logging.error(f"Error sending audio: {e}")
                await query.message.reply_text("خطا در ارسال فایل. لطفاً دوباره تلاش کنید.")

async def stats(update: Update, context):
    total_songs = len(SONGS)
    stats_text = f"📊 **آمار ربات Deep House Farsi**\n\n🎵 کل آهنگ‌ها: {total_songs}\n\n"
    for song_id, info in SONGS.items():
        stats_text += f"• {info['title']}: `{info['downloads']}` بار دانلود\n"
    
    await update.message.reply_text(stats_text, parse_mode="Markdown")

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("stats", stats))
application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, get_file_id))
application.add_handler(CallbackQueryHandler(button))

@app.route("/")
def index():
    return "Bot is running perfectly!", 200

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
