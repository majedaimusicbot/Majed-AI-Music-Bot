import os
import logging
import asyncio

from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)


# ==================================================
# تنظیمات
# ==================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# توکن را در Render > Environment Variables قرار بده
TOKEN = os.environ.get("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN در Environment Variables تنظیم نشده است")


YOUTUBE_URL = "https://www.youtube.com/@DeepHouse_Farsi?sub_confirmation=1"


# ==================================================
# لیست آهنگ‌ها
# ==================================================

SONGS = {
    "song_1": {
        "title": "🎵 بزن به سیم آخر",
        "file_id": "CQACAgQAAxkBAAMTaqfErP0p4AKJQHX5yGTqz06TmiIAAg8iAAIRZEBR7jMYGeE6jE9BA"
    }
}


# ==================================================
# Flask
# ==================================================

app = Flask(__name__)


# ==================================================
# Telegram Bot
# ==================================================

application = Application.builder().token(TOKEN).build()


# ==================================================
# کاربرانی که روی «من سابسکرایب کردم» زده‌اند
# ==================================================

verified_users = set()


# ==================================================
# ساخت دکمه‌ها
# ==================================================

def create_keyboard(user_id):

    # ----------------------------------------------
    # اگر کاربر تأیید کرده باشد
    # ----------------------------------------------

    if user_id in verified_users:

        keyboard = [
            [
                InlineKeyboardButton(
                    "❤️ سابسکرایب در یوتیوب",
                    url=YOUTUBE_URL
                )
            ]
        ]

        for song_id, song_info in SONGS.items():

            keyboard.append([
                InlineKeyboardButton(
                    f"🎵 دریافت آهنگ: {song_info['title']}",
                    callback_data=f"download:{song_id}"
                )
            ])

        return InlineKeyboardMarkup(keyboard)


    # ----------------------------------------------
    # حالت قفل
    # ----------------------------------------------

    keyboard = [
        [
            InlineKeyboardButton(
                "❤️ سابسکرایب در یوتیوب",
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


# ==================================================
# دستور Start
# ==================================================

async def start(update: Update, context):

    user_id = update.effective_user.id

    await update.message.reply_text(

        "🎵 به ربات دانلود آهنگ خوش آمدید!\n\n"

        "برای فعال شدن بخش دانلود:\n\n"

        "1️⃣ ابتدا روی دکمه «❤️ سابسکرایب در یوتیوب» بزنید.\n\n"

        "2️⃣ وارد کانال یوتیوب شوید و Subscribe کنید.\n\n"

        "3️⃣ به تلگرام برگردید.\n\n"

        "4️⃣ روی دکمه «✅ من سابسکرایب کردم» بزنید.\n\n"

        "بعد از آن بخش دانلود برای شما باز می‌شود. 👇",

        reply_markup=create_keyboard(user_id)
    )


# ==================================================
# مدیریت دکمه‌ها
# ==================================================

async def button(update: Update, context):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    data = query.data


    # ==================================================
    # من سابسکرایب کردم
    # ==================================================

    if data == "verify":

        # ثبت کاربر
        verified_users.add(user_id)

        # تغییر پیام و باز شدن دانلود
        await query.message.edit_text(

            "🎉 ممنون از حمایت شما!\n\n"

            "✅ بخش دانلود برای شما فعال شد.\n\n"

            "حالا می‌توانید آهنگ موردنظر را دریافت کنید. 🎵",

            reply_markup=create_keyboard(user_id)
        )

        await query.answer(
            "✅ دانلود آهنگ فعال شد!",
            show_alert=True
        )

        return


    # ==================================================
    # دانلود قفل
    # ==================================================

    if data == "locked":

        await query.answer(

            "🔒 ابتدا کانال یوتیوب را Subscribe کنید.\n\n"
            "بعد به تلگرام برگردید و روی «✅ من سابسکرایب کردم» بزنید.",

            show_alert=True
        )

        return


    # ==================================================
    # دانلود آهنگ
    # ==================================================

    if data.startswith("download:"):

        # بررسی فعال بودن دانلود
        if user_id not in verified_users:

            await query.answer(

                "🔒 ابتدا باید کانال یوتیوب را Subscribe کنید.",

                show_alert=True
            )

            return


        # گرفتن ID آهنگ
        song_id = data.split(":", 1)[1]


        # بررسی وجود آهنگ
        if song_id not in SONGS:

            await query.answer(
                "❌ آهنگ پیدا نشد.",
                show_alert=True
            )

            return


        song_info = SONGS[song_id]

        file_id = song_info["file_id"]

        chat_id = query.message.chat_id

        caption = (
            f"{song_info['title']}\n\n"
            "🔗 کانال ما: @DeepHouse_Farsi"
        )


        # پیام در حال ارسال
        await query.message.reply_text(

            f"⏳ در حال ارسال {song_info['title']}..."

        )


        # ==================================================
        # ارسال فایل
        # ==================================================

        sent = False


        send_functions = [

            lambda: context.bot.send_audio(
                chat_id=chat_id,
                audio=file_id,
                caption=caption
            ),

            lambda: context.bot.send_document(
                chat_id=chat_id,
                document=file_id,
                caption=caption
            ),

            lambda: context.bot.send_video(
                chat_id=chat_id,
                video=file_id,
                caption=caption
            ),

            lambda: context.bot.send_voice(
                chat_id=chat_id,
                voice=file_id,
                caption=caption
            ),

            lambda: context.bot.send_video_note(
                chat_id=chat_id,
                video_note=file_id
            )
        ]


        for send_func in send_functions:

            try:

                await send_func()

                sent = True

                break

            except Exception as e:

                logging.warning(
                    f"روش ارسال ناموفق بود: {e}"
                )

                continue


        # ==================================================
        # اگر هیچ روشی جواب نداد
        # ==================================================

        if not sent:

            await query.message.reply_text(

                "❌ خطا در ارسال فایل.\n\n"
                "لطفاً فایل‌آیدی آهنگ را بررسی کنید."

            )

        return


# ==================================================
# دریافت File ID
# ==================================================

async def get_file_id(update: Update, context):

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

            f"📁 فایل‌آیدی این {file_type}:\n\n"
            f"`{file_id}`",

            parse_mode="Markdown"

        )

    else:

        await msg.reply_text(

            "لطفاً یک فایل معتبر بفرستید."

        )


# ==================================================
# Handler ها
# ==================================================

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


# ==================================================
# صفحه اصلی Render
# ==================================================

@app.route("/")
def index():

    return "Bot is alive!", 200


# ==================================================
# Webhook
# ==================================================

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():

    try:

        json_data = request.get_json(force=True)

        update = Update.de_json(
            json_data,
            application.bot
        )


        async def process():

            await application.initialize()

            await application.process_update(update)


        asyncio.run(process())


        return "OK", 200


    except Exception as e:

        logging.exception(
            f"Webhook error: {e}"
        )

        return "ERROR", 500


# ==================================================
# اجرای برنامه
# ==================================================

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
