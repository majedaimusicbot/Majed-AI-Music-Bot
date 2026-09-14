import os
import logging
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

TOKEN = "8836665873:AAE7yM9_qhV6xgAv5VfnU3LDm-twXP910Ak"
YOUTUBE_URL = "https://www.youtube.com/@DeepHouse_Farsi?sub_confirmation=1"

# لیست آهنگ‌ها (برای اضافه کردن آهنگ‌های بعدی، کافی است به همین فرمت ادامه دهید)
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
    elif msg.video_note:
        file_id = msg.video_note.file_id
        file_type = "VideoNote"
        
    if file_id:
        await update.message.reply_text(f"📁 فایل‌آیدی این {file_type}:\n`{file_id}`", parse_mode="Markdown")
    else:
        await update.message.reply_text("لطفاً یک فایل معتبر بفرستید.")

async def button(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    song_id = query.data
    
    if song_id in SONGS:
        song_info = SONGS[song_id]
        await query.message.reply_text(f"از حمایت شما سپاسگزاریم! 🎉 در حال ارسال {song_info['title']}...")
        
        file_id = song_info["file_id"]
        chat_id = query.message.chat_id
        caption = f"{song_info['title']}\n\n🔗 کانال ما: @DeepHouse_Farsi"
        
        # سیستم هوشمند ارسال فایل با تست کردن روش‌های مختلف تلگرام
        sent = False
        for send_func in [
            lambda: context.bot.send_audio(chat_id=chat_id, audio=file_id, caption=caption),
            lambda: context.bot.send_video(chat_id=chat_id, video=file_id, caption=caption),
            lambda: context.bot.send_document(chat_id=chat_id, document=file_id, caption=caption),
            lambda: context.bot.send_voice(chat_id=chat_id, voice=file_id, caption=caption),
            lambda: context.bot.send_video_note(chat_id=chat_id, video_note=file_id)
        ]:
            try:
                await send_func()
                sent = True
                break
            except Exception:
                continue
                
        if not sent:
            await query.message.reply_text("خطا در ارسال فایل. لطفاً یک فایل‌آیدی جدید بفرستید.")

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
