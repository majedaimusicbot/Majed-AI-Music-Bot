import os
import asyncio
import threading
import logging

from flask import Flask, request

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)


# ==========================================
# LOGGING
# ==========================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


# ==========================================
# SETTINGS
# ==========================================

TOKEN = os.environ.get("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")


YOUTUBE_URL = "https://www.youtube.com/@DeepHouse_Farsi?sub_confirmation=1"


# ==========================================
# SONGS
# ==========================================

SONGS = {
    "song_1": {
        "title": "🎵 بزن به سیم آخر",
        "file_id": "CQACAgQAAxkBAAMTaqfErP0p4AKJQHX5yGTqz06TmiIAAg8iAAIRZEBR7jMYGeE6jE9BA"
    }
}


# ==========================================
# FLASK
# ==========================================

app = Flask(__name__)


# ==========================================
# TELEGRAM APPLICATION
# ==========================================

application = (
    Application.builder()
    .token(TOKEN)
    .updater(None)
    .build()
)


# کاربرانی که روی «من سابسکرایب کردم» زده‌اند
verified_users = set()


# ==========================================
# KEYBOARD
# ==========================================

def get_keyboard(user_id):

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


# ==========================================
# START
# ==========================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    await update.message.reply_text(
        "🎵 به ربات دانلود آهنگ خوش آمدید!\n\n"
        "برای فعال شدن دانلود:\n\n"
        "1️⃣ روی دکمه «❤️ سابسکرایب کانال یوتیوب» بزنید.\n"
        "2️⃣ وارد یوتیوب شوید و کانال را Subscribe کنید.\n"
        "3️⃣ به تلگرام برگردید.\n"
        "4️⃣ روی «✅ من سابسکرایب کردم» بزنید.\n\n"
        "بعد از آن دانلود آهنگ برای شما فعال می‌شود. 👇",
        reply_markup=get_keyboard(user_id)
    )


# ==========================================
# BUTTON
# ==========================================

async def button(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id
    data = query.data


    # ======================================
    # VERIFY
    # ======================================

    if data == "verify":

        verified_users.add(user_id)

        await query.message.edit_text(
            "🎉 ممنون از حمایت شما!\n\n"
            "بخش دانلود برای شما فعال شد. 🎵\n"
            "آهنگ موردنظر را انتخاب کنید:",
            reply_markup=get_keyboard(user_id)
        )

        await query.answer(
            "✅ دانلود فعال شد!",
            show_alert=True
        )

        return


    # ======================================
    # LOCKED
    # ======================================

    if data == "locked":

        await query.answer(
            "🔒 ابتدا کانال یوتیوب را Subscribe کنید و سپس «من سابسکرایب کردم» را بزنید.",
            show_alert=True
        )

        return


    # ======================================
    # DOWNLOAD
    # ======================================

    if data.startswith("download:"):

        # بررسی اینکه کاربر تأیید شده
        if user_id not in verified_users:

            await query.answer(
                "🔒 ابتدا باید کانال یوتیوب را Subscribe کنید.",
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

        except Exception:

            logging.exception("Error sending audio")

            await query.message.reply_text(
                "❌ خطا در ارسال آهنگ."
            )

        return


# ==========================================
# GET FILE ID
# ==========================================

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


# ==========================================
# HANDLERS
# ==========================================

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


# ==========================================
# HOME
# ==========================================

@app.route("/")
def index():

    return "Bot is alive!", 200


# ==========================================
# EVENT LOOP
# ==========================================

loop = asyncio.new_event_loop()


def bot_worker():

    asyncio.set_event_loop(loop)


    async def start_bot():

        await application.initialize()

        await application.start()


        render_url = os.environ.get(
            "RENDER_EXTERNAL_URL"
        )


        if render_url:

            webhook_url = (
                f"{render_url}/webhook"
            )

            await application.bot.set_webhook(
                url=webhook_url
            )

            logging.info(
                f"Webhook set: {webhook_url}"
            )

        else:

            logging.warning(
                "RENDER_EXTERNAL_URL is not set"
            )


    loop.run_until_complete(
        start_bot()
    )

    loop.run_forever()


# اجرای Bot در Thread جداگانه
threading.Thread(
    target=bot_worker,
    daemon=True
).start()


# ==========================================
# WEBHOOK
# ==========================================

@app.route(
    "/webhook",
    methods=["POST"]
)
def webhook():

    try:

        json_data = request.get_json(
            force=True
        )


        update = Update.de_json(
            json_data,
            application.bot
        )


        asyncio.run_coroutine_threadsafe(
            application.update_queue.put(update),
            loop
        )


        return "OK", 200


    except Exception:

        logging.exception(
            "Webhook error"
        )

        return "ERROR", 500


# ==========================================
# RUN
# ==========================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )


    app.run(
        host="0.0.0.0",
        port=port
    )
