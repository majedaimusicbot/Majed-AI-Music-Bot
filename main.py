import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

TOKEN = "8836665873:AAE7yM9_qhV6xgAv5VfnU3LDm-twXP910Ak"
YOUTUBE_URL = "https://www.youtube.com/@MajedAIMusic"
AUDIO_URL = "https://t.me/c/..."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔴 سابسکرایب در یوتیوب", url=YOUTUBE_URL)],
        [InlineKeyboardButton("✅ دریافت آهنگ", callback_data="get_audio")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "سلام! 🎵\nبرای دریافت فایل صوتی آهنگ، ابتدا کانال یوتیوب ما را سابسکرایب کنید و سپس روی دکمه‌ی «دریافت آهنگ» بزنید.",
        reply_markup=reply_markup
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "get_audio":
        await query.message.reply_text(f"ممنون از حمایت شما! ❤️\nاین هم لینک دانلود آهنگ:\n{AUDIO_URL}")

def main():
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    
    port = int(os.environ.get("PORT", 8080))
    webhook_url = os.environ.get("RENDER_EXTERNAL_URL")
    
    if webhook_url:
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            webhook_url=f"{webhook_url}/{TOKEN}"
        )
    else:
        application.run_polling()

if __name__ == "__main__":
    main()
