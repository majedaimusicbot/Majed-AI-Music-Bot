import os
import logging
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

TOKEN = "8836665873:AAE7yM9_qhV6xgAv5VfnU3LDm-twXP910Ak"
YOUTUBE_URL = "https://www.youtube.com/@MajedAIMusic"
AUDIO_URL = "https://t.me/..."

app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

async def start(update: Update, context):
    keyboard = [
        [InlineKeyboardButton("❤️ سابسکرایب در یوتیوب", url=YOUTUBE_URL)],
        [InlineKeyboardButton("🎵 دریافت آهنگ", callback_data="get_audio")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "برای دریافت فایل صوتی آهنگ، ابتدا کانال یوتیوب ما را سابسکرایب کنید و سپس روی دکمه «دریافت آهنگ» بزنید.",
        reply_markup=reply_markup
    )

async def button(update: Update, context):
    query = update.callback_query
    await query.answer()
    if query.data == "get_audio":
        await query.message.reply_text(AUDIO_URL)

application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(button))

@app.route("/")
def index():
    return "Bot is alive!", 200

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_data = request.get_json(force=True)
    update = Update.de_json(json_data, application.bot)
    
    # اجرای صحیح پردازش آپدیت در لوپ رویداد ربات
    async def process():
        await application.initialize()
        await application.process_update(update)
    
    import asyncio
    asyncio.run(process())
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
