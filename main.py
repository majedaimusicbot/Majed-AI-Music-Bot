import os
import logging
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

TOKEN = "8836665873:AAE7yM9_qhV6xgAv5VfnU3LDm-twXP910Ak"
YOUTUBE_URL = "https://www.youtube.com/@DeepHouse_Farsi?sub_confirmation=1"

# اینجا فایل‌آیدی (file_id) موزیک خود را قرار دهید
AUDIO_FILE_ID = "BAACAgQAAxkBAAE..." 

app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

async def start(update: Update, context):
    keyboard = [
        [InlineKeyboardButton("❤️ سابسکرایب در یوتیوب", url=YOUTUBE_URL)],
        [InlineKeyboardButton("✅ تایید و دریافت آهنگ", callback_data="get_song")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "برای دریافت فایل صوتی آهنگ، ابتدا روی دکمه‌ی بالا بزنید و کانال یوتیوب ما را سابسکرایب کنید، سپس روی «تایید و دریافت آهنگ» بزنید.",
        reply_markup=reply_markup
    )

async def button(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    if query.data == "get_song":
        await query.message.reply_text("از حمایت شما سپاسگزاریم! 🎉 در حال ارسال آهنگ...")
        try:
            await context.bot.send_audio(
                chat_id=query.message.chat_id,
                audio=AUDIO_FILE_ID,
                caption="🎵 موزیک جدید شما از کانال Deep House Farsi"
            )
        except Exception as e:
            logging.error(f"Error sending audio: {e}")
            await query.message.reply_text("خطا در ارسال فایل. لطفاً فایل‌آیدی را بررسی کنید.")

application.add_handler(CommandHandler("start", start))
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
