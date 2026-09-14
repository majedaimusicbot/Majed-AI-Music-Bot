import os
import json
import uuid
import asyncio
import threading
import logging

from flask import Flask, jsonify

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
    filters,
    ContextTypes,
)


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================================================
# CONFIG
# =========================================================

TOKEN = os.environ.get("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "BOT_TOKEN environment variable is missing."
    )


ADMIN_ID_RAW = os.environ.get("ADMIN_ID")

if not ADMIN_ID_RAW:
    raise RuntimeError(
        "ADMIN_ID environment variable is missing."
    )


try:
    ADMIN_ID = int(ADMIN_ID_RAW)
except ValueError:
    raise RuntimeError(
        "ADMIN_ID must be a numeric Telegram user ID."
    )


# YouTube channel
YOUTUBE_URL = (
    "https://www.youtube.com/"
    "@DeepHouse_Farsi?sub_confirmation=1"
)


# Telegram channel
TELEGRAM_CHANNEL = "@majedaimusic"


# Database
DB_FILE = "songs_db.json"

PAGE_SIZE = 10


# =========================================================
# FLASK
# =========================================================

app = Flask(__name__)


# =========================================================
# DATABASE
# =========================================================

def load_songs():
    """
    Load songs from songs_db.json.
    """

    if not os.path.exists(DB_FILE):
        return {}

    try:
        with open(
            DB_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            content = f.read().strip()

            if not content:
                return {}

            data = json.loads(content)

            if isinstance(data, dict):
                return data

            return {}

    except Exception:
        logger.exception(
            "Could not read songs_db.json"
        )
        return {}


def save_songs(songs):
    """
    Safely save songs database.
    """

    tmp_file = DB_FILE + ".tmp"

    try:

        with open(
            tmp_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                songs,
                f,
                ensure_ascii=False,
                indent=2,
            )

        os.replace(
            tmp_file,
            DB_FILE,
        )

    except Exception:
        logger.exception(
            "Could not save songs_db.json"
        )


SONGS = load_songs()


# =========================================================
# TELEGRAM APPLICATION
# =========================================================

telegram_app = (
    Application
    .builder()
    .token(TOKEN)
    .build()
)


# =========================================================
# MAIN MENU
# =========================================================

def main_menu():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "❤️ عضویت در یوتیوب",
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
                callback_data="latest_songs",
            ),
        ],

    ])


# =========================================================
# ARCHIVE MENU
# =========================================================

def archive_menu(page=0):

    global SONGS

    SONGS = load_songs()

    items = list(SONGS.items())

    total = len(items)

    if total == 0:

        return (
            "📂 **آرشیو آهنگ‌ها خالی است.**",

            InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 منوی اصلی",
                        callback_data="main_menu",
                    )
                ]
            ]),
        )


    max_page = (total - 1) // PAGE_SIZE

    page = max(
        0,
        min(page, max_page)
    )


    start = page * PAGE_SIZE

    end = start + PAGE_SIZE

    page_items = items[start:end]


    keyboard = []


    for song_id, info in page_items:

        title = str(
            info.get(
                "title",
                "آهنگ بدون نام"
            )
        )

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

        "🎵 **آرشیو آهنگ‌های Majed AI Music**\n\n"

        f"🎧 تعداد کل آهنگ‌ها: {total}\n"

        f"📄 صفحه {page + 1} از {max_page + 1}\n\n"

        "آهنگ موردنظر را انتخاب کنید:"
    )


    return (
        text,
        InlineKeyboardMarkup(keyboard)
    )


# =========================================================
# /START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return


    context.user_data["waiting_for_search"] = False


    welcome_text = (

        "✨ **به Majed AI Music خوش آمدید**\n\n"

        "🎧 آرشیو اختصاصی آهنگ‌های ما\n\n"

        "برای دریافت آهنگ موردنظر، "
        "یکی از گزینه‌های زیر را انتخاب کنید ❤️"
    )


    await update.message.reply_text(

        welcome_text,

        reply_markup=main_menu(),

        parse_mode="Markdown",

    )


# =========================================================
# /ADD
# =========================================================

async def add_song_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.effective_user:
        return


    if update.effective_user.id != ADMIN_ID:

        await update.message.reply_text(
            "⛔ شما دسترسی مدیریتی ندارید."
        )

        return


    if not context.args:

        await update.message.reply_text(

            "⚠️ **روش افزودن آهنگ:**\n\n"

            "`/add نام آهنگ`\n\n"

            "سپس فایل صوتی آهنگ را ارسال کنید.",

            parse_mode="Markdown",

        )

        return


    title = "🎵 " + " ".join(context.args)


    context.user_data["pending_title"] = title


    await update.message.reply_text(

        f"✅ عنوان ثبت شد:\n\n"
        f"{title}\n\n"
        "حالا فایل صوتی آهنگ را ارسال کنید."
    )


# =========================================================
# /STATS
# =========================================================

async def stats(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.effective_user:
        return


    if update.effective_user.id != ADMIN_ID:

        await update.message.reply_text(
            "⛔ شما دسترسی مدیریتی ندارید."
        )

        return


    global SONGS

    SONGS = load_songs()


    total_songs = len(SONGS)


    total_downloads = sum(

        int(
            info.get(
                "downloads",
                0
            )
        )

        for info in SONGS.values()

    )


    lines = [

        "📊 **گزارش آمار Majed AI Music**",

        "",

        f"🎵 تعداد آهنگ‌ها: {total_songs}",

        f"📥 مجموع دانلودها: {total_downloads}",

        "",

    ]


    for info in SONGS.values():

        title = str(
            info.get(
                "title",
                "بدون نام"
            )
        )

        downloads = int(
            info.get(
                "downloads",
                0
            )
        )


        lines.append(

            f"• {title}: "
            f"📥 {downloads} دانلود"

        )


    await update.message.reply_text(

        "\n".join(lines),

        parse_mode="Markdown",

    )


# =========================================================
# MEDIA + SEARCH
# =========================================================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    global SONGS


    if not update.message:
        return


    if not update.effective_user:
        return


    user_id = update.effective_user.id


    # -----------------------------------------------------
    # USER SEARCH
    # -----------------------------------------------------

    if user_id != ADMIN_ID:

        if context.user_data.get(
            "waiting_for_search"
        ):

            context.user_data[
                "waiting_for_search"
            ] = False


            query_text = (
                update.message.text or ""
            ).strip()


            if not query_text:

                await update.message.reply_text(
                    "❌ عبارت جستجو خالی است."
                )

                return


            SONGS = load_songs()


            matched = []


            for song_id, info in SONGS.items():

                title = str(
                    info.get(
                        "title",
                        ""
                    )
                )


                if (
                    query_text.casefold()
                    in title.casefold()
                ):

                    matched.append(
                        (song_id, info)
                    )


            keyboard = []


            for song_id, info in matched[:10]:

                keyboard.append([

                    InlineKeyboardButton(

                        str(
                            info.get(
                                "title",
                                "آهنگ"
                            )
                        ),

                        callback_data=(
                            f"sel_{song_id}"
                        ),

                    )

                ])


            keyboard.append([

                InlineKeyboardButton(
                    "🔙 منوی اصلی",
                    callback_data="main_menu",
                )

            ])


            if matched:

                text = (

                    f"🔎 نتیجه جستجو برای "
                    f"«{query_text}»\n\n"

                    f"تعداد نتایج: {len(matched)}"
                )

            else:

                text = (

                    f"❌ آهنگی برای "
                    f"«{query_text}» پیدا نشد."
                )


            await update.message.reply_text(

                text,

                reply_markup=(
                    InlineKeyboardMarkup(keyboard)
                ),

            )


        return


    # -----------------------------------------------------
    # ADMIN ADD SONG
    # -----------------------------------------------------

    msg = update.message


    file_id = None


    if msg.audio:

        file_id = msg.audio.file_id

    elif msg.voice:

        file_id = msg.voice.file_id

    elif msg.document:

        file_id = msg.document.file_id


    if not file_id:

        # اگر ادمین در حالت جستجو نیست
        # و فایل هم نیست، کاری نکن
        return


    if (
        "pending_title"
        not in context.user_data
    ):

        await msg.reply_text(

            "📁 فایل دریافت شد.\n\n"

            "برای ثبت آهنگ ابتدا بنویسید:\n"

            "`/add نام آهنگ`",

            parse_mode="Markdown",

        )

        return


    title = context.user_data.pop(
        "pending_title"
    )


    SONGS = load_songs()


    song_id = uuid.uuid4().hex[:8]


    SONGS[song_id] = {

        "title": title,

        "file_id": file_id,

        "downloads": 0,

    }


    save_songs(SONGS)


    await msg.reply_text(

        "🎉 **آهنگ با موفقیت اضافه شد!**\n\n"

        f"🎵 {title}\n"

        f"🆔 `{song_id}`",

        parse_mode="Markdown",

    )


# =========================================================
# BUTTON HANDLER
# =========================================================

async def button(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    global SONGS


    query = update.callback_query


    if not query:
        return


    await query.answer()


    SONGS = load_songs()


    data = query.data


    # -----------------------------------------------------
    # NOOP
    # -----------------------------------------------------

    if data == "noop":
        return


    # -----------------------------------------------------
    # MAIN MENU
    # -----------------------------------------------------

    if data == "main_menu":

        context.user_data[
            "waiting_for_search"
        ] = False


        await query.message.edit_text(

            "✨ **به Majed AI Music خوش آمدید**\n\n"

            "🎧 آرشیو اختصاصی آهنگ‌های ما\n\n"

            "برای دریافت آهنگ موردنظر، "
            "یکی از گزینه‌های زیر را انتخاب کنید ❤️",

            reply_markup=main_menu(),

            parse_mode="Markdown",

        )

        return


    # -----------------------------------------------------
    # ARCHIVE
    # -----------------------------------------------------

    if data.startswith("archive_"):

        try:

            page = int(
                data.split(
                    "_",
                    1
                )[1]
            )

        except ValueError:

            page = 0


        text, markup = archive_menu(page)


        await query.message.edit_text(

            text,

            reply_markup=markup,

            parse_mode="Markdown",

        )

        return


    # -----------------------------------------------------
    # SEARCH START
    # -----------------------------------------------------

    if data == "search_start":

        context.user_data[
            "waiting_for_search"
        ] = True


        keyboard = InlineKeyboardMarkup([

            [

                InlineKeyboardButton(

                    "🔙 منوی اصلی",

                    callback_data="main_menu",

                )

            ]

        ])


        await query.message.edit_text(

            "🔎 **جستجوی آهنگ**\n\n"

            "نام یا بخشی از نام آهنگ را "
            "همینجا ارسال کنید.",

            reply_markup=keyboard,

            parse_mode="Markdown",

        )

        return


    # -----------------------------------------------------
    # LATEST SONGS
    # -----------------------------------------------------

    if data == "latest_songs":

        items = list(
            SONGS.items()
        )


        latest = items[-10:][::-1]


        keyboard = []


        for song_id, info in latest:

            keyboard.append([

                InlineKeyboardButton(

                    str(
                        info.get(
                            "title",
                            "آهنگ"
                        )
                    ),

                    callback_data=(
                        f"sel_{song_id}"
                    ),

                )

            ])


        keyboard.append([

            InlineKeyboardButton(

                "🔙 منوی اصلی",

                callback_data="main_menu",

            )

        ])


        if latest:

            text = (

                "🔥 **جدیدترین آهنگ‌های Majed AI Music**\n\n"

                "آهنگ موردنظر را انتخاب کنید:"
            )

        else:

            text = (
                "🔥 هنوز آهنگی اضافه نشده است."
            )


        await query.message.edit_text(

            text,

            reply_markup=(
                InlineKeyboardMarkup(keyboard)
            ),

            parse_mode="Markdown",

        )

        return


    # -----------------------------------------------------
    # SELECT SONG
    # -----------------------------------------------------

    if data.startswith("sel_"):

        song_id = data.split(
            "_",
            1
        )[1]


        if song_id not in SONGS:

            await query.message.edit_text(

                "❌ این آهنگ دیگر در آرشیو موجود نیست.",

                reply_markup=InlineKeyboardMarkup([

                    [

                        InlineKeyboardButton(

                            "🔙 منوی اصلی",

                            callback_data="main_menu",

                        )

                    ]

                ]),

            )

            return


        song = SONGS[song_id]


        # اگر قبلاً تایید کرده
        if context.user_data.get(
            "youtube_confirmed"
        ):

            keyboard = InlineKeyboardMarkup([

                [

                    InlineKeyboardButton(

                        "⬇️ دانلود آهنگ",

                        callback_data=(
                            f"download_{song_id}"
                        ),

                    )

                ],

                [

                    InlineKeyboardButton(

                        "🔙 آرشیو آهنگ‌ها",

                        callback_data="archive_0",

                    )

                ],

            ])


            await query.message.edit_text(

                f"🎵 **{song['title']}**\n\n"

                "✅ عضویت شما قبلاً تأیید شده است.\n"

                "برای دریافت آهنگ روی دانلود بزنید.",

                reply_markup=keyboard,

                parse_mode="Markdown",

            )


        else:

            keyboard = InlineKeyboardMarkup([

                [

                    InlineKeyboardButton(

                        "❤️ عضویت در یوتیوب",

                        url=YOUTUBE_URL,

                    )

                ],

                [

                    InlineKeyboardButton(

                        "✅ سابسکرایب کردم",

                        callback_data=(
                            f"verify_{song_id}"
                        ),

                    )

                ],

                [

                    InlineKeyboardButton(

                        "🔙 آرشیو",

                        callback_data="archive_0",

                    )

                ],

            ])


            await query.message.edit_text(

                f"🔐 **تأیید عضویت**\n\n"

                f"🎵 آهنگ: {song['title']}\n\n"

                "ابتدا در یوتیوب عضو شوید و سپس "
                "روی «سابسکرایب کردم» بزنید.",

                reply_markup=keyboard,

                parse_mode="Markdown",

            )


        return


    # -----------------------------------------------------
    # VERIFY SUBSCRIPTION
    # -----------------------------------------------------

    if data.startswith("verify_"):

        song_id = data.split(
            "_",
            1
        )[1]


        if song_id not in SONGS:

            await query.message.edit_text(
                "❌ آهنگ پیدا نشد."
            )

            return


        # -------------------------------------------------
        # HONOR SYSTEM
        # YouTube subscription is NOT actually verified.
        # -------------------------------------------------

        context.user_data[
            "youtube_confirmed"
        ] = True


        keyboard = InlineKeyboardMarkup([

            [

                InlineKeyboardButton(

                    "⬇️ دانلود آهنگ",

                    callback_data=(
                        f"download_{song_id}"
                    ),

                )

            ],

            [

                InlineKeyboardButton(

                    "🔙 آرشیو آهنگ‌ها",

                    callback_data="archive_0",

                )

            ],

        ])


        await query.message.edit_text(

            "✅ **عضویت تأیید شد**\n\n"

            "حالا می‌توانید آهنگ را دریافت کنید.",

            reply_markup=keyboard,

            parse_mode="Markdown",

        )

        return


    # -----------------------------------------------------
    # DOWNLOAD
    # -----------------------------------------------------

    if data.startswith("download_"):

        song_id = data.split(
            "_",
            1
        )[1]


        if not context.user_data.get(
            "youtube_confirmed"
        ):

            keyboard = InlineKeyboardMarkup([

                [

                    InlineKeyboardButton(

                        "❤️ عضویت در یوتیوب",

                        url=YOUTUBE_URL,

                    )

                ],

                [

                    InlineKeyboardButton(

                        "🔙 آرشیو",

                        callback_data="archive_0",

                    )

                ],

            ])


            await query.message.edit_text(

                "🔒 ابتدا باید عضویت یوتیوب "
                "را تأیید کنید.",

                reply_markup=keyboard,

            )

            return


        if song_id not in SONGS:

            await query.message.edit_text(
                "❌ آهنگ پیدا نشد."
            )

            return


        song = SONGS[song_id]


        file_id = song.get(
            "file_id"
        )


        if not file_id:

            await query.message.edit_text(

                "❌ فایل این آهنگ ثبت نشده است.\n"

                "لطفاً به ادمین اطلاع دهید."

            )

            return


        chat_id = query.message.chat_id


        await query.message.edit_text(

            f"⏳ در حال ارسال **{song['title']}** ...",

            parse_mode="Markdown",

        )


        # -------------------------------------------------
        # CAPTION
        # -------------------------------------------------

        caption = (

            f"🎵 {song['title']}\n\n"

            f"🔗 کانال رسمی ما: {TELEGRAM_CHANNEL}"
        )


        sent = False


        # -------------------------------------------------
        # TRY AUDIO
        # -------------------------------------------------

        try:

            await context.bot.send_audio(

                chat_id=chat_id,

                audio=file_id,

                caption=caption,

            )

            sent = True


        except Exception:

            logger.exception(
                "send_audio failed"
            )


        # -------------------------------------------------
        # FALLBACK DOCUMENT
        # -------------------------------------------------

        if not sent:

            try:

                await context.bot.send_document(

                    chat_id=chat_id,

                    document=file_id,

                    caption=caption,

                )

                sent = True


            except Exception:

                logger.exception(
                    "send_document failed"
                )


        # -------------------------------------------------
        # SUCCESS
        # -------------------------------------------------

        if sent:

            SONGS[song_id]["downloads"] = (

                int(
                    SONGS[song_id].get(
                        "downloads",
                        0
                    )
                )
                + 1

            )


            save_songs(SONGS)


            await context.bot.send_message(

                chat_id=chat_id,

                text=(

                    "🎧 آهنگ با موفقیت ارسال شد!\n\n"

                    "برای دریافت آهنگ‌های دیگر "
                    "از آرشیو استفاده کنید."
                ),

                reply_markup=InlineKeyboardMarkup([

                    [

                        InlineKeyboardButton(

                            "🎵 آرشیو آهنگ‌ها",

                            callback_data="archive_0",

                        )

                    ],

                    [

                        InlineKeyboardButton(

                            "🔙 منوی اصلی",

                            callback_data="main_menu",

                        )

                    ],

                ]),

            )


        else:

            await context.bot.send_message(

                chat_id=chat_id,

                text=(

                    "❌ ارسال فایل ناموفق بود.\n\n"

                    "لطفاً به ادمین اطلاع دهید."
                ),

            )

        return


# =========================================================
# HANDLERS
# =========================================================

telegram_app.add_handler(
    CommandHandler(
        "start",
        start
    )
)


telegram_app.add_handler(
    CommandHandler(
        "add",
        add_song_command
    )
)


telegram_app.add_handler(
    CommandHandler(
        "stats",
        stats
    )
)


telegram_app.add_handler(

    MessageHandler(

        filters.AUDIO
        | filters.VOICE
        | filters.Document.ALL
        | (
            filters.TEXT
            & ~filters.COMMAND
        ),

        handle_message,

    )

)


telegram_app.add_handler(
    CallbackQueryHandler(
        button
    )
)


# =========================================================
# BOT LOOP
# =========================================================

bot_loop = asyncio.new_event_loop()

bot_thread = None

bot_start_error = None


def run_bot():

    global bot_start_error


    asyncio.set_event_loop(
        bot_loop
    )


    async def setup():

        logger.info(
            "Initializing Telegram application..."
        )


        await telegram_app.initialize()


        # حذف Webhook قدیمی
        await telegram_app.bot.delete_webhook(
            drop_pending_updates=True
        )


        await telegram_app.start()


        if telegram_app.updater is None:

            raise RuntimeError(
                "Telegram updater is unavailable."
            )


        await telegram_app.updater.start_polling(

            allowed_updates=Update.ALL_TYPES,

            drop_pending_updates=True,

        )


        logger.info(
            "========================================"
        )

        logger.info(
            "Majed AI Music Bot is RUNNING"
        )

        logger.info(
            "Telegram polling is ACTIVE"
        )

        logger.info(
            "Webhook is DISABLED"
        )

        logger.info(
            "========================================"
        )


    try:

        bot_loop.run_until_complete(
            setup()
        )


        bot_loop.run_forever()


    except Exception as exc:

        bot_start_error = repr(exc)

        logger.exception(
            "BOT START FAILED"
        )


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

    return (
        "Majed AI Music Bot is running!",
        200
    )


@app.get("/health")
def health():

    polling_running = False


    try:

        polling_running = bool(

            telegram_app.updater
            and telegram_app.updater.running

        )

    except Exception:

        polling_running = False


    return jsonify({

        "status": "ok",

        "telegram_running":
            telegram_app.running,

        "polling_running":
            polling_running,

        "bot_thread_alive":
            bot_thread.is_alive(),

        "bot_start_error":
            bot_start_error,

    }), 200


# =========================================================
# LOCAL RUN
# =========================================================

if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=int(
            os.environ.get(
                "PORT",
                10000
            )
        ),

    )
