import os
import asyncio
import threading
import logging

from flask import Flask, request

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)


# =========================
# تنظیمات
# =========================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

TOKEN = os.environ.get("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN در Environment Variables تنظیم نشده است")


YOUTUBE_URL = "https://www.youtube.com/@DeepHouse_Farsi?sub_confirmation=1"


# =========================
# آهنگ‌ها
# =========================

SONGS = {
    "song_1": {
        "title": "🎵 بزن به سیم آخر",

        # file_id آهنگ
        "file_id": "CQACAgQAAxkBAAMTaqfErP0p4AKJQHX5yGTqz06TmiIAAg8iAAIRZEBR7jMYGeE6jE9BA"
    }
}


# =========================
# Flask
# =========================

app = Flask(__name__)


# =========================
# Telegram Application
# =========================

application = (
    Application.builder()
    .token(TOKEN)
    .updater(None)
    .build()
)


# وضعیت کاربرانی که روی
# «من سابسکرایب کردم» زده‌اند
verified_users = set()


# =========================
# ساخت منوی اصلی
# =========================

def main_keyboard(user_id):

    # اگر کاربر تأیید کرده باشد
    if user_id in verified_users:

        keyboard = [
            [
                InlineKeyboardButton(
                    "❤️ سابسکرایب کانال یوتیوب",
                    url=YOUTUBE_URL
                )
            ]
        ]

        for song_id, song_info in SONGS.items():
            keyboard.append([
                InlineKeyboardButton(
                    f"🎵 دانلود {song_info['title']}",
                    callback_data=f"download:{song_id}"
                )
            ])

        return InlineKeyboardMarkup(keyboard)

    # حالت قفل
    keyboard = [
        [
            InlineKeyboardButton(
                "❤️ سابسکرایب کانال یوتیوب",
                url=YOUTUBE_URL
            )
        ],
        [
            InlineKeyboardButton(
                "🔒 دانلود آهنگ",
                callback_data="locked"
            )
        ],
        [
            InlineKeyboardButton(
                "✅ من سابسکرایب کردم",
                callback_data="verify"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================
# /start
# =========================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    await update.message.reply_text(
        "🎵 به ربات دانلود آهنگ خوش آمدید!\n\n"
        "برای فعال شدن بخش دانلود:\n\n"
        "1️⃣ روی «❤️ سابسکرایب کانال یوتیوب» بزنید\n"
        "2️⃣ وارد یوتیوب شوید و کانال را Subscribe کنید\n"
        "3️⃣ به تلگرام برگردید\n"
        "4️⃣ روی «✅ من سابسکرایب کردم» بزنید\n\n"
        "بعد از آن بخش دانلود برای شما فعال می‌شود. 👇",
        reply_markup=main_keyboard(user_id)
    )


# =========================
# دکمه‌ها
# =========================

async def button(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id
    data = query.data

    # -------------------------
    # دکمه من سابسکرایب کردم
    # -------------------------

    if data == "verify":

        verified_users.add(user_id)

        await query.answer(
            "✅ بخش دانلود فعال شد!",
            show_alert=True
        )

        await query.message.edit_text(
            "🎉 ممنون از حمایت شما!\n\n"
            "عضویت شما ثبت شد.\n"
            "حالا می‌توانید آهنگ موردنظر را دانلود کنید. 🎵",
            reply_markup=main_keyboard(user_id)
        )

        return


    # -------------------------
    # دکمه دانلود قفل
    # -------------------------

    if data == "locked":

        await query.answer(
            "🔒 ابتدا کانال یوتیوب را Subscribe کنید و سپس «من سابسکرایب کردم» را بزنید.",
            show_alert=True
        )

        return


    # -------------------------
    # دانلود آهنگ
    # -------------------------

    if data.startswith("download:"):

        # بررسی دوباره
        if user_id not in verified_users:

            await query.answer(
                "🔒 ابتدا باید سابسکرایب کنید.",
                show_alert=True
            )

            return

        song_id = data.split(":", 1)[1]

        if song_id not in SONGS:
            await query.answer(
                "❌ آهنگ پیدا نشد.",
                show_alert=True
            )
            return

        song_info = SONGS[song_id]

        await query.message.reply_text(
            f"⏳ در حال ارسال {song_info['title']}..."
        )

        try:

            await context.bot.send_audio(
                chat_id=query.message.chat_id,
                audio=song_info["file_id"],
                caption=(
                    f"{song_info['title']}\n\n"
                    "🔗 کانال ما: @DeepHouse_Farsi"
                )
            )

        except Exception as e:

            logging.exception("خطا در ارسال آهنگ")

            await query.message.reply_text(
                "❌ متأسفانه ارسال آهنگ با خطا مواجه شد.\n"
                "لطفاً دوباره تلاش کنید."
            )

        return


# =========================
# دریافت File ID
# =========================

async def get_file_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    msg = update.message

    if not msg:
        return

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

        await msg.reply_text(
            f"📁 File ID ({file_type}):\n\n"
            f"`{file_id}`",
            parse_mode="Markdown"
        )

    else:

        await msg.reply_text(
            "لطفاً یک فایل صوتی یا فایل معتبر ارسال کنید."
        )


# =========================
# Handlerها
# =========================

application.add_handler(
    CommandHandler("start", start)
)

application.add_handler(
    CallbackQueryHandler(button)
)

application.add_handler(
    MessageHandler(
        filters.ALL & ~filters.COMMAND,
        get_file_id
    )
)


# =========================
# صفحه اصلی Render
# =========================

@app.route("/")
def index():

    return "Bot is alive!", 200


# =========================
# Webhook
# =========================

loop = asyncio.new_event_loop()


def bot_worker():

    asyncio.set_event_loop(loop)

    async def start_bot():

        await application.initialize()

        await application.start()

        render_url = os.environ.get("RENDER_EXTERNAL_URL")

        if render_url:

            webhook_url = f"{render_url}/webhook"

            await application.bot.set_webhook(
                url=webhook_url
            )

            logging.info(
                f"Webhook set to: {webhook_url}"
            )

        else:

            logging.warning(
                "RENDER_EXTERNAL_URL تنظیم نشده است"
            )

    loop.run_until_complete(start_bot())

    loop.run_forever()


threading.Thread(
    target=bot_worker,
    daemon=True
).start()


# =========================
# دریافت Update از Telegram
# =========================

@app.route("/webhook", methods=["POST"])
def webhook():

    try:

        json_data = request.get_json(force=True)

        update = Update.de_json(
            json_data,
            application.bot
        )

        asyncio.run_coroutine_threadsafe(
            application.update_queue.put(update),
            loop
        )

        return "OK", 200

    except Exception as e:

        logging.exception(
            "Webhook error"
        )

        return "ERROR", 500


# =========================
# اجرای Flask
# =========================

if __name__ == "__main__":

    port = int(
        os.environ.get("PORT", 10000)
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
