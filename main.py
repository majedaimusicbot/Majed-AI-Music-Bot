import os
import json
import uuid
import asyncio
import threading
import logging

from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# =========================================================
# CONFIG
# =========================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is missing.")

ADMIN_ID_RAW = os.environ.get("ADMIN_ID")
if not ADMIN_ID_RAW:
    raise RuntimeError("ADMIN_ID environment variable is missing.")

try:
    ADMIN_ID = int(ADMIN_ID_RAW)
except ValueError:
    raise RuntimeError("ADMIN_ID must be a numeric Telegram user ID.")

YOUTUBE_URL = "https://www.youtube.com/@DeepHouse_Farsi?sub_confirmation=1"
DB_FILE = "songs_db.json"
PAGE_SIZE = 10

# =========================================================
# DATABASE
# =========================================================

def load_songs():
    if not os.path.exists(DB_FILE):
        return {}

    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {}
            data = json.loads(content)
            return data if isinstance(data, dict) else {}
    except Exception:
        logger.exception("Could not read songs_db.json")
        return {}


def save_songs(songs):
    try:
        tmp_file = DB_FILE + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(songs, f, ensure_ascii=False, indent=2)
        os.replace(tmp_file, DB_FILE)
    except Exception:
        logger.exception("Could not save songs_db.json")


SONGS = load_songs()

# =========================================================
# FLASK
# =========================================================

app = Flask(__name__)

# =========================================================
# TELEGRAM APPLICATION
# =========================================================

telegram_app = Application.builder().token(TOKEN).build()

bot_loop = asyncio.new_event_loop()
bot_thread = None
bot_ready = threading.Event()
bot_start_error = None


def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❤️ عضویت در یوتیوب", url=YOUTUBE_URL)],
        [InlineKeyboardButton("🎵 آرشیو آهنگ‌ها", callback_data="archive_0")],
        [
            InlineKeyboardButton("🔎 جستجوی آهنگ", callback_data="search_start"),
            InlineKeyboardButton("🔥 جدیدترین‌ها", callback_data="latest_songs"),
        ],
    ])


def archive_menu(page=0):
    global SONGS
    SONGS = load_songs()

    items = list(SONGS.items())
    total = len(items)

    if total == 0:
        return (
            "📂 **آرشیو آهنگ‌ها خالی است.**",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")]
            ]),
        )

    max_page = (total - 1) // PAGE_SIZE
    page = max(0, min(page, max_page))

    start = page * PAGE_SIZE
    end = start + PAGE_SIZE

    keyboard = []

    for song_id, info in items[start:end]:
        title = str(info.get("title", "آهنگ بدون نام"))
        keyboard.append([
            InlineKeyboardButton(
                title,
                callback_data=f"sel_{song_id}",
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
            f"📄 {page + 1}/{max_page + 1}",
            callback_data="noop",
        )
    )

    if end < total:
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

    text = (
        "🎵 **آرشیو آهنگ‌های Deep House Farsi**\n\n"
        f"تعداد کل آهنگ‌ها: {total}\n"
        f"صفحه {page + 1} از {max_page + 1}\n\n"
        "آهنگ موردنظر را انتخاب کنید:"
    )

    return text, InlineKeyboardMarkup(keyboard)


# =========================================================
# COMMANDS
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✨ **به Deep House Farsi خوش آمدید**\n\n"
        "🎧 آرشیو اختصاصی آهنگ‌های ما\n\n"
        "برای دریافت آهنگ موردنظر، یکی از گزینه‌های زیر را انتخاب کنید ❤️",
        reply_markup=main_menu(),
        parse_mode="Markdown",
    )


async def add_song_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ شما دسترسی مدیریتی ندارید.")
        return

    if not context.args:
        await update.message.reply_text(
            "⚠️ روش استفاده:\n\n"
            "/add نام آهنگ\n\n"
            "سپس فایل صوتی را ارسال کنید."
        )
        return

    title = "🎵 " + " ".join(context.args)
    context.user_data["pending_title"] = title

    await update.message.reply_text(
        f"✅ عنوان ثبت شد:\n{title}\n\n"
        "حالا فایل صوتی را ارسال کنید."
    )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ شما دسترسی مدیریتی ندارید.")
        return

    global SONGS
    SONGS = load_songs()

    total = len(SONGS)
    total_downloads = sum(
        int(info.get("downloads", 0))
        for info in SONGS.values()
    )

    lines = [
        "📊 **گزارش آمار ربات**",
        "",
        f"🎵 تعداد آهنگ‌ها: {total}",
        f"📥 مجموع دانلودها: {total_downloads}",
        "",
    ]

    for info in SONGS.values():
        lines.append(
            f"• {info.get('title', 'بدون نام')}: "
            f"{int(info.get('downloads', 0))} دانلود"
        )

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
    )


# =========================================================
# ADMIN MEDIA / USER SEARCH
# =========================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global SONGS

    if not update.message:
        return

    user_id = update.effective_user.id

    # User search
    if user_id != ADMIN_ID:
        if context.user_data.get("waiting_for_search"):
            context.user_data["waiting_for_search"] = False

            query_text = (update.message.text or "").strip()
            if not query_text:
                await update.message.reply_text("❌ عبارت جستجو خالی است.")
                return

            SONGS = load_songs()

            matched = [
                (song_id, info)
                for song_id, info in SONGS.items()
                if query_text.casefold()
                in str(info.get("title", "")).casefold()
            ]

            keyboard = [
                [
                    InlineKeyboardButton(
                        str(info.get("title", "آهنگ")),
                        callback_data=f"sel_{song_id}",
                    )
                ]
                for song_id, info in matched[:10]
            ]

            keyboard.append([
                InlineKeyboardButton(
                    "🔙 منوی اصلی",
                    callback_data="main_menu",
                )
            ])

            if matched:
                await update.message.reply_text(
                    f"🔎 نتیجه جستجو برای «{query_text}»\n\n"
                    f"تعداد نتایج: {len(matched)}",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
            else:
                await update.message.reply_text(
                    f"❌ آهنگی برای «{query_text}» پیدا نشد.",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
        return

    # Admin adds a song
    msg = update.message
    file_id = None

    if msg.audio:
        file_id = msg.audio.file_id
    elif msg.voice:
        file_id = msg.voice.file_id
    elif msg.document:
        file_id = msg.document.file_id

    if not file_id:
        return

    if "pending_title" not in context.user_data:
        await msg.reply_text(
            "📁 فایل دریافت شد.\n\n"
            "برای ثبت آهنگ ابتدا بنویسید:\n"
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

    await msg.reply_text(
        f"🎉 **آهنگ با موفقیت اضافه شد!**\n\n"
        f"🎵 {title}\n"
        f"🆔 `{song_id}`",
        parse_mode="Markdown",
    )


# =========================================================
# BUTTONS
# =========================================================

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global SONGS

    query = update.callback_query
    await query.answer()

    SONGS = load_songs()
    data = query.data
    user_id = query.from_user.id

    if data == "noop":
        return

    if data == "main_menu":
        context.user_data["waiting_for_search"] = False

        await query.message.edit_text(
            "✨ **به Deep House Farsi خوش آمدید**\n\n"
            "🎧 آرشیو اختصاصی آهنگ‌های ما\n\n"
            "برای دریافت آهنگ موردنظر، یکی از گزینه‌های زیر را انتخاب کنید ❤️",
            reply_markup=main_menu(),
            parse_mode="Markdown",
        )
        return

    if data.startswith("archive_"):
        page = int(data.split("_", 1)[1])
        text, markup = archive_menu(page)

        await query.message.edit_text(
            text,
            reply_markup=markup,
            parse_mode="Markdown",
        )
        return

    if data == "search_start":
        context.user_data["waiting_for_search"] = True

        await query.message.edit_text(
            "🔎 **جستجوی آهنگ**\n\n"
            "نام یا بخشی از نام آهنگ را همینجا ارسال کنید.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🔙 منوی اصلی",
                    callback_data="main_menu",
                )]
            ]),
            parse_mode="Markdown",
        )
        return

    if data == "latest_songs":
        items = list(SONGS.items())
        latest = items[-10:][::-1]

        keyboard = [
            [
                InlineKeyboardButton(
                    str(info.get("title", "آهنگ")),
                    callback_data=f"sel_{song_id}",
                )
            ]
            for song_id, info in latest
        ]

        keyboard.append([
            InlineKeyboardButton(
                "🔙 منوی اصلی",
                callback_data="main_menu",
            )
        ])

        await query.message.edit_text(
            "🔥 **جدیدترین آهنگ‌ها**\n\n"
            + (
                "آهنگی هنوز اضافه نشده است."
                if not latest
                else "آهنگ موردنظر را انتخاب کنید:"
            ),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )
        return

    if data.startswith("sel_"):
        song_id = data.split("_", 1)[1]

        if song_id not in SONGS:
            await query.message.edit_text(
                "❌ این آهنگ دیگر در آرشیو موجود نیست.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        "🔙 منوی اصلی",
                        callback_data="main_menu",
                    )]
                ]),
            )
            return

        song = SONGS[song_id]

        # If this user already confirmed once, show direct download button.
        if context.user_data.get("youtube_confirmed"):
            keyboard = [
                [InlineKeyboardButton(
                    "⬇️ دانلود آهنگ",
                    callback_data=f"download_{song_id}",
                )],
                [InlineKeyboardButton(
                    "🔙 آرشیو",
                    callback_data="archive_0",
                )],
            ]

            await query.message.edit_text(
                f"🎵 **{song['title']}**\n\n"
                "عضویت شما قبلاً تأیید شده است.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )
        else:
            keyboard = [
                [InlineKeyboardButton(
                    "❤️ عضویت در یوتیوب",
                    url=YOUTUBE_URL,
                )],
                [InlineKeyboardButton(
                    "✅ سابسکرایب کردم",
                    callback_data=f"verify_{song_id}",
                )],
                [InlineKeyboardButton(
                    "🔙 آرشیو",
                    callback_data="archive_0",
                )],
            ]

            await query.message.edit_text(
                f"🔐 **تأیید عضویت**\n\n"
                f"🎵 آهنگ: {song['title']}\n\n"
                "ابتدا در یوتیوب عضو شوید و سپس روی "
                "«سابسکرایب کردم» بزنید.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )
        return

    if data.startswith("verify_"):
        song_id = data.split("_", 1)[1]

        if song_id not in SONGS:
            await query.message.edit_text("❌ آهنگ پیدا نشد.")
            return

        # IMPORTANT:
        # This is an honor-system confirmation.
        # Telegram/YouTube do not verify the YouTube subscription here.
        context.user_data["youtube_confirmed"] = True

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "⬇️ دانلود آهنگ",
                callback_data=f"download_{song_id}",
            )],
            [InlineKeyboardButton(
                "🔙 آرشیو آهنگ‌ها",
                callback_data="archive_0",
            )],
        ])

        await query.message.edit_text(
            "✅ **عضویت تأیید شد**\n\n"
            "حالا می‌توانید آهنگ را دریافت کنید.",
            reply_markup=keyboard,
            parse_mode="Markdown",
        )
        return

    if data.startswith("download_"):
        song_id = data.split("_", 1)[1]

        if not context.user_data.get("youtube_confirmed"):
            await query.message.edit_text(
                "🔒 ابتدا باید عضویت یوتیوب را تأیید کنید.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        "❤️ عضویت در یوتیوب",
                        url=YOUTUBE_URL,
                    )],
                    [InlineKeyboardButton(
                        "🔙 آرشیو",
                        callback_data="archive_0",
                    )],
                ]),
            )
            return

        if song_id not in SONGS:
            await query.message.edit_text("❌ آهنگ پیدا نشد.")
            return

        song = SONGS[song_id]
        chat_id = query.message.chat_id
        file_id = song.get("file_id")

        if not file_id:
            await query.message.edit_text(
                "❌ فایل این آهنگ ثبت نشده است. به ادمین اطلاع دهید."
            )
            return

        await query.message.edit_text(
            f"⏳ در حال ارسال **{song['title']}** ...",
            parse_mode="Markdown",
        )

        caption = (
            f"🎵 {song['title']}\n\n"
            "🔗 کانال رسمی ما: @DeepHouse_Farsi"
        )

        sent = False

        try:
            await context.bot.send_audio(
                chat_id=chat_id,
                audio=file_id,
                caption=caption,
            )
            sent = True
        except Exception:
            logger.exception("send_audio failed")

        if not sent:
            try:
                await context.bot.send_document(
                    chat_id=chat_id,
                    document=file_id,
                    caption=caption,
                )
                sent = True
            except Exception:
                logger.exception("send_document failed")

        if sent:
            SONGS[song_id]["downloads"] = int(
                SONGS[song_id].get("downloads", 0)
            ) + 1
            save_songs(SONGS)

            await context.bot.send_message(
                chat_id=chat_id,
                text="🎧 برای دریافت آهنگ‌های دیگر، از آرشیو استفاده کنید.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        "🎵 آرشیو آهنگ‌ها",
                        callback_data="archive_0",
                    )],
                    [InlineKeyboardButton(
                        "🔙 منوی اصلی",
                        callback_data="main_menu",
                    )],
                ]),
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ ارسال فایل ناموفق بود. لطفاً به ادمین اطلاع دهید.",
            )


# =========================================================
# HANDLERS
# =========================================================

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("add", add_song_command))
telegram_app.add_handler(CommandHandler("stats", stats))

telegram_app.add_handler(
    MessageHandler(
        filters.AUDIO
        | filters.VOICE
        | filters.Document.ALL
        | (filters.TEXT & ~filters.COMMAND),
        handle_message,
    )
)

telegram_app.add_handler(CallbackQueryHandler(button))


# =========================================================
# POLLING THREAD
# =========================================================
# We intentionally use polling instead of the previous custom
# Flask webhook queue. This avoids the Flask/Gunicorn/asyncio
# webhook lifecycle problem that was causing /start to be ignored.

def run_bot():
    global bot_start_error

    asyncio.set_event_loop(bot_loop)

    async def setup():
        # Remove any old webhook before polling.
        await telegram_app.initialize()
        await telegram_app.bot.delete_webhook(drop_pending_updates=True)

        await telegram_app.start()

        if telegram_app.updater is None:
            raise RuntimeError("Telegram updater is unavailable.")

        await telegram_app.updater.start_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
        )

        logger.info("========================================")
        logger.info("Telegram bot is RUNNING with POLLING")
        logger.info("Webhook removed; polling is active")
        logger.info("========================================")

    try:
        bot_loop.run_until_complete(setup())
        bot_ready.set()
        bot_loop.run_forever()
    except Exception as exc:
        bot_start_error = repr(exc)
        logger.exception("BOT START FAILED")
        bot_ready.set()


bot_thread = threading.Thread(
    target=run_bot,
    name="telegram-bot",
    daemon=True,
)
bot_thread.start()


# =========================================================
# FLASK ROUTES
# =========================================================

@app.get("/")
def index():
    return "Majed AI Music Bot is running!", 200


@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "telegram_running": telegram_app.running,
        "polling_running": bool(
            telegram_app.updater
            and telegram_app.updater.running
        ),
        "bot_thread_alive": bot_thread.is_alive(),
        "bot_start_error": bot_start_error,
    }), 200


# No /webhook route is needed because Telegram polling is used.


# =========================================================
# LOCAL
# =========================================================

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
    )
