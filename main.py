import os
import json
import uuid
import asyncio
import logging
import threading

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

# =========================
# Logging
# =========================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================
# Environment
# =========================

TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID_RAW = os.environ.get("ADMIN_ID")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN تنظیم نشده است.")

if not ADMIN_ID_RAW:
    raise RuntimeError("ADMIN_ID تنظیم نشده است.")

try:
    ADMIN_ID = int(ADMIN_ID_RAW)
except ValueError:
    raise RuntimeError("ADMIN_ID باید عدد باشد.")


# =========================
# Settings
# =========================

YOUTUBE_URL = (
    "https://www.youtube.com/@DeepHouse_Farsi?sub_confirmation=1"
)

DB_FILE = "songs_db.json"
PAGE_SIZE = 10


# =========================
# Flask
# =========================

app = Flask(__name__)


# =========================
# Database
# =========================

def load_songs():
    if not os.path.exists(DB_FILE):
        return {}

    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()

        if not content:
            return {}

        data = json.loads(content)

        if not isinstance(data, dict):
            logger.error("songs_db.json باید یک object باشد.")
            return {}

        return data

    except Exception:
        logger.exception("خطا هنگام خواندن songs_db.json")
        return {}


def save_songs(songs):
    try:
        temp_file = DB_FILE + ".tmp"

        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(
                songs,
                f,
                ensure_ascii=False,
                indent=4,
            )

        os.replace(temp_file, DB_FILE)

    except Exception:
        logger.exception("خطا هنگام ذخیره songs_db.json")


SONGS = load_songs()


# =========================
# Main Menu
# =========================

def main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "❤️ عضویت در کانال یوتیوب",
                url=YOUTUBE_URL,
            )
        ],
        [
            InlineKeyboardButton(
                "🎵 آرشیو آهنگ‌ها",
                callback_data="archive_0",
            )
        ],
        [
            InlineKeyboardButton(
                "🔎 جستجوی آهنگ",
                callback_data="search_start",
            ),
            InlineKeyboardButton(
                "🔥 جدیدترین‌ها",
                callback_data="latest",
            ),
        ],
    ])


def back_button():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔙 بازگشت به منوی اصلی",
                callback_data="main_menu",
            )
        ]
    ])


# =========================
# /start
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["waiting_for_search"] = False

    text = (
        "✨ **به Deep House Farsi خوش آمدید** ✨\n\n"
        "🎧 آرشیو اختصاصی موسیقی\n\n"
        "از منوی زیر آهنگ موردنظرتان را انتخاب کنید:"
    )

    if update.message:
        await update.message.reply_text(
            text,
            reply_markup=main_menu(),
            parse_mode="Markdown",
        )


# =========================
# /add
# =========================

async def add_song(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(
            "⛔ شما دسترسی مدیریتی ندارید."
        )
        return

    if not context.args:
        await update.message.reply_text(
            "⚠️ روش افزودن آهنگ:\n\n"
            "/add نام آهنگ\n\n"
            "سپس فایل صوتی را ارسال کنید."
        )
        return

    title = "🎵 " + " ".join(context.args)

    context.user_data["pending_title"] = title

    await update.message.reply_text(
        f"✅ عنوان ثبت شد:\n\n"
        f"{title}\n\n"
        f"حالا فایل صوتی آهنگ را ارسال کنید."
    )


# =========================
# Media / Search Text
# =========================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    global SONGS

    user_id = update.effective_user.id

    # -------------------------
    # Search
    # -------------------------

    if (
        update.message
        and update.message.text
        and user_id != ADMIN_ID
        and context.user_data.get("waiting_for_search")
    ):

        context.user_data["waiting_for_search"] = False

        search_text = update.message.text.strip().lower()

        SONGS = load_songs()

        results = []

        for song_id, song in SONGS.items():

            title = str(song.get("title", "")).lower()

            if search_text in title:
                results.append((song_id, song))

        if not results:

            await update.message.reply_text(
                "❌ آهنگی با این نام پیدا نشد.",
                reply_markup=back_button(),
            )

            return

        keyboard = []

        for song_id, song in results[:10]:

            keyboard.append([
                InlineKeyboardButton(
                    f"🎧 {song.get('title', 'بدون عنوان')}",
                    callback_data=f"song_{song_id}",
                )
            ])

        keyboard.append([
            InlineKeyboardButton(
                "🔙 منوی اصلی",
                callback_data="main_menu",
            )
        ])

        await update.message.reply_text(
            f"🔎 **نتایج جستجو**\n\n"
            f"تعداد نتایج: {len(results)}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

        return

    # -------------------------
    # Admin media
    # -------------------------

    if user_id != ADMIN_ID:
        return

    if not update.message:
        return

    message = update.message

    file_id = None

    if message.audio:
        file_id = message.audio.file_id

    elif message.voice:
        file_id = message.voice.file_id

    elif message.document:
        file_id = message.document.file_id

    if not file_id:
        return

    if "pending_title" not in context.user_data:

        await message.reply_text(
            "📁 فایل دریافت شد.\n\n"
            "برای اضافه کردن آن ابتدا بنویسید:\n"
            "/add نام آهنگ"
        )

        return

    title = context.user_data.pop("pending_title")

    SONGS = load_songs()

    song_id = uuid.uuid4().hex[:8]

    SONGS[song_id] = {
        "title": title,
        "file_id": file_id,
        "downloads": 0,
    }

    save_songs(SONGS)

    await message.reply_text(
        "🎉 **آهنگ با موفقیت اضافه شد!**\n\n"
        f"🎵 عنوان: {title}\n"
        f"🆔 شناسه: `{song_id}`",
        parse_mode="Markdown",
    )


# =========================
# Buttons
# =========================

async def button(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    global SONGS

    query = update.callback_query

    await query.answer()

    SONGS = load_songs()

    data = query.data

    # =========================
    # Main Menu
    # =========================

    if data == "main_menu":

        context.user_data["waiting_for_search"] = False

        await query.message.edit_text(
            "✨ **به Deep House Farsi خوش آمدید** ✨\n\n"
            "🎧 آرشیو اختصاصی موسیقی\n\n"
            "از منوی زیر آهنگ موردنظرتان را انتخاب کنید:",
            reply_markup=main_menu(),
            parse_mode="Markdown",
        )

        return

    # =========================
    # Archive
    # =========================

    if data.startswith("archive_"):

        page = int(data.split("_")[1])

        songs = list(SONGS.items())

        total = len(songs)

        if total == 0:

            await query.message.edit_text(
                "📂 آرشیو آهنگ‌ها فعلاً خالی است.",
                reply_markup=back_button(),
            )

            return

        total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE

        if page < 0:
            page = 0

        if page >= total_pages:
            page = total_pages - 1

        start_index = page * PAGE_SIZE
        end_index = start_index + PAGE_SIZE

        current_songs = songs[start_index:end_index]

        keyboard = []

        for song_id, song in current_songs:

            keyboard.append([
                InlineKeyboardButton(
                    f"🎧 {song.get('title', 'بدون عنوان')}",
                    callback_data=f"song_{song_id}",
                )
            ])

        navigation = []

        if page > 0:

            navigation.append(
                InlineKeyboardButton(
                    "⬅️ قبلی",
                    callback_data=f"archive_{page - 1}",
                )
            )

        navigation.append(
            InlineKeyboardButton(
                f"📄 {page + 1}/{total_pages}",
                callback_data="noop",
            )
        )

        if page < total_pages - 1:

            navigation.append(
                InlineKeyboardButton(
                    "بعدی ➡️",
                    callback_data=f"archive_{page + 1}",
                )
            )

        keyboard.append(navigation)

        keyboard.append([
            InlineKeyboardButton(
                "🔙 منوی اصلی",
                callback_data="main_menu",
            )
        ])

        await query.message.edit_text(
            "📂 **آرشیو آهنگ‌ها**\n\n"
            "آهنگ موردنظر را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

        return

    # =========================
    # Latest
    # =========================

    if data == "latest":

        songs = list(SONGS.items())

        latest = songs[-10:]
        latest.reverse()

        keyboard = []

        for song_id, song in latest:

            keyboard.append([
                InlineKeyboardButton(
                    f"🔥 {song.get('title', 'بدون عنوان')}",
                    callback_data=f"song_{song_id}",
                )
            ])

        keyboard.append([
            InlineKeyboardButton(
                "🔙 منوی اصلی",
                callback_data="main_menu",
            )
        ])

        if not latest:

            text = "🔥 هنوز آهنگی اضافه نشده است."

        else:

            text = "🔥 **جدیدترین آهنگ‌ها**\n\n"

            text += "آخرین آهنگ‌های اضافه‌شده:"

        await query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )

        return

    # =========================
    # Search
    # =========================

    if data == "search_start":

        context.user_data["waiting_for_search"] = True

        await query.message.edit_text(
            "🔎 **جستجوی آهنگ**\n\n"
            "نام یا بخشی از نام آهنگ را ارسال کنید:",
            reply_markup=back_button(),
            parse_mode="Markdown",
        )

        return

    # =========================
    # Nothing
    # =========================

    if data == "noop":
        return

    # =========================
    # Song Selected
    # =========================

    if data.startswith("song_"):

        song_id = data.replace("song_", "", 1)

        if song_id not in SONGS:

            await query.message.edit_text(
                "❌ این آهنگ دیگر وجود ندارد.",
                reply_markup=back_button(),
            )

            return

        song = SONGS[song_id]

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "❤️ عضویت در یوتیوب",
                    url=YOUTUBE_URL,
                )
            ],
            [
                InlineKeyboardButton(
                    "✅ سابسکرایب کردم؛ دریافت آهنگ",
                    callback_data=f"verify_{song_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    "🔙 بازگشت",
                    callback_data="main_menu",
                )
            ],
        ])

        await query.message.edit_text(
            "🔐 **دریافت آهنگ**\n\n"
            f"🎵 {song.get('title', 'بدون عنوان')}\n\n"
            "1️⃣ ابتدا در کانال یوتیوب عضو شوید.\n"
            "2️⃣ سپس روی دکمه «سابسکرایب کردم» بزنید.\n"
            "3️⃣ فایل برای شما ارسال می‌شود.",
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

        return

    # =========================
    # Verify / Download
    # =========================

    if data.startswith("verify_"):

        song_id = data.replace("verify_", "", 1)

        if song_id not in SONGS:

            await query.message.edit_text(
                "❌ این آهنگ پیدا نشد.",
                reply_markup=back_button(),
            )

            return

        song = SONGS[song_id]

        title = song.get("title", "آهنگ")

        file_id = song.get("file_id")

        if not file_id:

            await query.message.edit_text(
                "❌ فایل این آهنگ در دسترس نیست.",
                reply_markup=back_button(),
            )

            return

        await query.message.edit_text(
            f"🎉 **ممنون از حمایت شما!**\n\n"
            f"🎵 {title}\n\n"
            "📥 در حال ارسال فایل...",
            parse_mode="Markdown",
        )

        chat_id = query.message.chat_id

        caption = (
            f"🎵 {title}\n\n"
            "🔗 کانال رسمی: @DeepHouse_Farsi"
        )

        sent = False

        # Try audio
        try:

            await context.bot.send_audio(
                chat_id=chat_id,
                audio=file_id,
                caption=caption,
            )

            sent = True

        except Exception:
            logger.exception("ارسال به صورت audio شکست خورد.")

        # Try document
        if not sent:

            try:

                await context.bot.send_document(
                    chat_id=chat_id,
                    document=file_id,
                    caption=caption,
                )

                sent = True

            except Exception:
                logger.exception("ارسال به صورت document شکست خورد.")

        if sent:

            try:
                SONGS[song_id]["downloads"] = (
                    int(SONGS[song_id].get("downloads", 0)) + 1
                )

                save_songs(SONGS)

            except Exception:
                logger.exception("خطا در ثبت دانلود.")

            await context.bot.send_message(
                chat_id=chat_id,
                text="👇 برای دریافت آهنگ‌های دیگر:",
                reply_markup=back_button(),
            )

        else:

            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ ارسال فایل ناموفق بود. لطفاً به ادمین اطلاع دهید.",
            )

        return


# =========================
# Statistics
# =========================

async def stats(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if update.effective_user.id != ADMIN_ID:

        await update.message.reply_text(
            "⛔ شما دسترسی مدیریتی ندارید."
        )

        return

    songs = load_songs()

    total_songs = len(songs)

    total_downloads = 0

    for song in songs.values():

        try:
            total_downloads += int(
                song.get("downloads", 0)
            )
        except Exception:
            pass

    text = (
        "📊 **آمار ربات**\n\n"
        f"🎵 تعداد آهنگ‌ها: {total_songs}\n"
        f"📥 مجموع دانلودها: {total_downloads}\n\n"
    )

    if songs:

        text += "📋 آمار آهنگ‌ها:\n\n"

        for song in songs.values():

            text += (
                f"• {song.get('title', 'بدون عنوان')}\n"
                f"  📥 {song.get('downloads', 0)} دانلود\n\n"
            )

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
    )


# =========================
# Telegram Application
# =========================

telegram_app = (
    Application.builder()
    .token(TOKEN)
    .build()
)

telegram_app.add_handler(
    CommandHandler("start", start)
)

telegram_app.add_handler(
    CommandHandler("add", add_song)
)

telegram_app.add_handler(
    CommandHandler("stats", stats)
)

telegram_app.add_handler(
    CallbackQueryHandler(button)
)

telegram_app.add_handler(
    MessageHandler(
        filters.AUDIO
        | filters.VOICE
        | filters.Document.ALL
        | (filters.TEXT & ~filters.COMMAND),
        handle_message,
    )
)


# =========================
# Dedicated Telegram Loop
# =========================

bot_loop = asyncio.new_event_loop()


def run_bot():

    asyncio.set_event_loop(bot_loop)

    async def setup():

        logger.info("Initializing Telegram application...")

        await telegram_app.initialize()

        logger.info("Starting Telegram application...")

        await telegram_app.start()

        logger.info(
            f"Telegram application running: {telegram_app.running}"
        )

        if not RENDER_EXTERNAL_URL:

            raise RuntimeError(
                "RENDER_EXTERNAL_URL در Render تنظیم نشده است."
            )

        webhook_url = (
            RENDER_EXTERNAL_URL.rstrip("/")
            + "/webhook"
        )

        await telegram_app.bot.set_webhook(
            url=webhook_url,
            drop_pending_updates=True,
        )

        logger.info(
            f"Webhook set successfully: {webhook_url}"
        )

    bot_loop.run_until_complete(setup())

    logger.info("Telegram event loop is running.")

    bot_loop.run_forever()


bot_thread = threading.Thread(
    target=run_bot,
    daemon=True,
    name="telegram-bot-loop",
)

bot_thread.start()


# =========================
# Flask Routes
# =========================

@app.route("/", methods=["GET"])
def index():

    return "Deep House Farsi Bot is running!", 200


@app.route("/health", methods=["GET"])
def health():

    return {
        "status": "healthy",
        "telegram_running": telegram_app.running,
        "bot_loop_running": bot_loop.is_running(),
    }, 200


@app.route("/webhook", methods=["POST"])
def webhook():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):

        return "Invalid JSON", 400

    try:

        update = Update.de_json(
            data,
            telegram_app.bot,
        )

        if update:

            bot_loop.call_soon_threadsafe(
                telegram_app.update_queue.put_nowait,
                update,
            )

        return "OK", 200

    except Exception:

        logger.exception(
            "Error while processing webhook"
        )

        return "Internal Server Error", 500


# =========================
# Local Development
# =========================

if __name__ == "__main__":

    port = int(
        os.environ.get("PORT", 10000)
    )

    app.run(
        host="0.0.0.0",
        port=port,
    )
