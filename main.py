import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler

# توکن ربات شما
TOKEN = "8836665873:AAE7yM9_qhV6xgAv5VfnU3LDm-twXP910Ak"
# لینک کانال یوتیوب شما
YOUTUBE_URL = "https://www.youtube.com/@MajedAIMusic"  # لینک یوتیوب خود را اینجا بگذارید
# لینک دانلود یا فایل صوتی آهنگ
AUDIO_URL = "https://t.me/c/..." # لینک فایل صوتی یا آهنگ خود را اینجا بگذارید

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
        # ارسال آهنگ به کاربر
        await query.message.reply_text(f"ممنون از حمایت شما! ❤️\nاین هم لینک دانلود آهنگ:\n{AUDIO_URL}")

def main():
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    
    # اجرای ربات با پورت وب‌هوک یا پویایی ساده
    port = int(os.environ.get("PORT", 8080))
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        webhook_url=os.environ.get("RENDER_EXTERNAL_URL", "") + "/" + TOKEN
    )

if __name__ == "__main__":
    main()
