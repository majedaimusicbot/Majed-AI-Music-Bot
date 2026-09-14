import os
import logging
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

TOKEN = "8836665873:AAE7yM9_qhV6xgAv5VfnU3LDm-twXP910Ak"
YOUTUBE_URL = "https://www.youtube.com/@DeepHouse_Farsi?sub_confirmation=1"

# لیست آهنگ‌ها
SONGS = {
    "song_1": {
        "title": "🎵 بزن به سیم آخر",
        "file_id": "CQACAgQAAxkBAAMTaqfErP0p4AKJQHX5yGTqz06TmiIAAg8iAAIRZEBR7jMYGeE6jE9BA"
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
    await update.message.reply_text(
        "برای دریافت فایل‌های صوتی، ابتدا روی دکمه‌ی بالا بزنید و کانال یوتیوب ما را سابسکرایب کنید، سپس روی دکمه‌ی دریافت آهنگ بزنید.",
        reply_markup=reply_markup
    )

async def get_file_id(update: Update, context):
    # گرفتن فایل‌آیدی از هر نوع فایلی (صوتی، ویدیو، سند و...)
    msg = update.message
    file_id = None
    file_type = "نامشخص"
    
    if msg.audio:
        file_id = msg.audio.file_id
        file_type = "Audio"
    elif msg.voice:
        file_id = msg.voice.file_id
        file_type = "Voice"
    elif msg.video:
        file_id = msg.video.file_id
        file_type = "Video"
    elif msg.document:
        file_id = msg.document.file_id
        file_type = "Document"
        
    if file_id:
        await update.message.reply_text(f"📁 فایل‌آیدی این {file_type}:\n`{file_id}`", parse_mode="Markdown")
    else:
        await update.message.reply_text("لطفاً یک فایل صوتی یا ویدیو بفرستید.")

async def button(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    song_id = query.data
    
    if song_id in SONGS:
        song_info = SONGS[song_id]
        await query.message.reply_text(f"از حمایت شما سپاسگزاریم! 🎉 در حال ارسال {song_info['title']}...")
        try:
            # ارسال امن فایل بدون توجه به نوع فرمت (صوتی یا ویدیو)
            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=song_info["file_id"],
                caption=f"{song_info['title']}\n\n🔗 کانال ما: @DeepHouse_Farsi"
            )
        except Exception as e:
            logging.error(f"Error sending file: {e}")
            # اگر سند نشد، به عنوان ویدیو تست کند
            try:
                await context.bot.send_video(
                    chat_id=query.message.chat_id,
                    video=song_info["file_id"],
                    caption=f"{song_info['title']}\n\n🔗 کانال ما: @DeepHouse_Farsi"
                )
            except Exception as e2:
                logging.error(f"Error sending video: {e2}")
                await query.message.reply_text("خطا در ارسال فایل. لطفاً فایل را به صورت صوتی استاندارد (MP3) دوباره به ربات بفرستید تا فایل‌آیدی جدید بگیرید.")

application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, get_file_id))
application.add_handler(CallbackQueryHandler(button))

@app.route("/")
def index():
    return "Bot is alive!", 200

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
