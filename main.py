import os
import json
import uuid
import asyncio
import threading
import logging
import time

from flask import Flask, jsonify, request

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

# جلوگیری از نمایش اطلاعات حساس Telegram در لاگ
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)


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

    ADMIN_ID = int(
        ADMIN_ID_RAW
    )

except ValueError:

    raise RuntimeError(
        "ADMIN_ID must be a numeric Telegram user ID."
    )


# =========================================================
# RENDER WEBHOOK
# =========================================================

RENDER_EXTERNAL_URL = os.environ.get(
    "RENDER_EXTERNAL_URL"
)

CUSTOM_WEBHOOK_URL = os.environ.get(
    "WEBHOOK_URL"
)

WEBHOOK_SECRET = os.environ.get(
    "WEBHOOK_SECRET"
)


if CUSTOM_WEBHOOK_URL:

    WEBHOOK_URL = (
        CUSTOM_WEBHOOK_URL.rstrip("/")
        + "/telegram"
    )

elif RENDER_EXTERNAL_URL:

    WEBHOOK_URL = (
        RENDER_EXTERNAL_URL.rstrip("/")
        + "/telegram"
    )

else:

    WEBHOOK_URL = None


# =========================================================
# YOUTUBE
# =========================================================

YOUTUBE_URL = (
    "https://www.youtube.com/"
    "@DeepHouse_Farsi?sub_confirmation=1"
)


# =========================================================
# TELEGRAM CHANNEL
# =========================================================

TELEGRAM_CHANNEL = "@majedaimusic"


# =========================================================
# DATABASE
# =========================================================

DB_FILE = "songs_db.json"

PAGE_SIZE = 10


# =========================================================
# FLASK
# =========================================================

app = Flask(__name__)


# =========================================================
# DATABASE FUNCTIONS
# =========================================================

def load_songs():

    if not os.path.exists(DB_FILE):
        return {}

    try:

        with open(
            DB_FILE,
            "r",
            encoding="utf-8",
        ) as f:

            content = f.read().strip()

            if not content:
                return {}

            data = json.loads(
                content
            )

            if isinstance(
                data,
                dict,
            ):

                return data

            return {}

    except Exception:

        logger.exception(
            "Could not read songs_db.json"
        )

        return {}


def save_songs(songs):

    tmp_file = (
        DB_FILE
        + ".tmp"
    )

    try:

        with open(
            tmp_file,
            "w",
            encoding="utf-8",
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
# STATISTICS
# =========================================================

def get_total_songs():

    global SONGS

    SONGS = load_songs()

    return len(
        SONGS
    )


def get_total_downloads():

    global SONGS

    SONGS = load_songs()

    total = 0

    for info in SONGS.values():

        try:

            total += int(
                info.get(
                    "downloads",
                    0,
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            continue

    return total


# =========================================================
# MAIN MENU
# =========================================================

def main_menu():

    total_songs = (
        get_total_songs()
    )

    total_downloads = (
        get_total_downloads()
    )

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "❤️ حمایت با Subscribe در یوتیوب 🔴",
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
                "🔥 جدیدترین‌ها",
                callback_data="latest_songs",
            ),

            InlineKeyboardButton(
                "🔎 جستجوی آهنگ‌ها",
                callback_data="search_start",
            ),
        ],

        [
            InlineKeyboardButton(
                f"🎧 آهنگ‌ها: {total_songs}",
                callback_data="archive_0",
            ),

            InlineKeyboardButton(
                f"📥 دانلودها: {total_downloads}",
                callback_data="noop",
            ),
        ],

    ])


def main_menu_text():

    total_songs = (
        get_total_songs()
    )

    total_downloads = (
        get_total_downloads()
    )

    return (

        "✨ به Majed AI Music خوش آمدید\n\n"

        "🎧 آرشیو اختصاصی موسیقی\n"
        "🎵 جدیدترین آهنگ‌ها و موزیک‌های ما\n\n"

        f"🎧 آهنگ‌ها: {total_songs}     "
        f"📥 دانلودها: {total_downloads}\n\n"

        "برای دریافت آهنگ موردنظرت وارد آرشیو شو. ❤️\n\n"

        "اگر موسیقی‌های ما رو دوست داری، "
        "با یک Subscribe رایگان از ما حمایت کن. 🔴"

    )


# =========================================================
# YOUTUBE GATE
# =========================================================

def youtube_gate_keyboard(
    song_id
):

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "🔴 Subscribe در یوتیوب ❤️",
                url=YOUTUBE_URL,
            )
        ],

        [
            InlineKeyboardButton(
                "✅ انجام دادم — دریافت آهنگ",
                callback_data=(
                    f"youtube_confirm_{song_id}"
                ),
            )
        ],

        [
            InlineKeyboardButton(
                "🔙 انتخاب آهنگ دیگر",
                callback_data="archive_0",
            )
        ],

    ])


def youtube_gate_text(
    song
):

    return (

        "🚨⚠️ فقط یک مرحله تا دریافت آهنگ باقی مانده\n\n"

        f"🎵 {song['title']}\n\n"

        "اگر هنوز Subscribe نکردی، "
        "اول در یوتیوب عضو شو. ❤️\n\n"

        "🔴 بعد به ربات برگرد و "
        "«انجام دادم» رو بزن."

    )


# =========================================================
# SECOND WARNING
# =========================================================

def youtube_second_warning_text(
    song
):

    return (

        "⚠️ هنوز این مرحله کامل نشده!\n\n"

        "🔴 اول در یوتیوب Subscribe کن،\n"
        "بعد دوباره «انجام دادم» رو بزن."

    )


# =========================================================
# PER-SONG CONFIRMATION
# =========================================================

def get_confirmation_attempts(
    context
):

    attempts = context.user_data.get(
        "youtube_confirmation_attempts"
    )

    if not isinstance(
        attempts,
        dict,
    ):

        attempts = {}

        context.user_data[
            "youtube_confirmation_attempts"
        ] = attempts

    return attempts


def get_song_attempts(
    context,
    song_id,
):

    attempts = (
        get_confirmation_attempts(
            context
        )
    )

    try:

        return int(
            attempts.get(
                song_id,
                0,
            )
        )

    except (
        TypeError,
        ValueError,
    ):

        return 0


def increment_song_attempts(
    context,
    song_id,
):

    attempts = (
        get_confirmation_attempts(
            context
        )
    )

    current = (
        get_song_attempts(
            context,
            song_id,
        )
    )

    current += 1

    attempts[
        song_id
    ] = current

    return current


def get_confirmed_songs(
    context
):

    confirmed = context.user_data.get(
        "youtube_confirmed_songs"
    )

    if not isinstance(
        confirmed,
        set,
    ):

        confirmed = set()

        context.user_data[
            "youtube_confirmed_songs"
        ] = confirmed

    return confirmed


def is_song_confirmed(
    context,
    song_id,
):

    confirmed = (
        get_confirmed_songs(
            context
        )
    )

    return (
        song_id
        in confirmed
    )


def confirm_song(
    context,
    song_id,
):

    confirmed = (
        get_confirmed_songs(
            context
        )
    )

    confirmed.add(
        song_id
    )


# =========================================================
# PROCESSING LOCK
# =========================================================

def get_processing_songs(
    context
):

    processing = context.user_data.get(
        "youtube_processing_songs"
    )

    if not isinstance(
        processing,
        set,
    ):

        processing = set()

        context.user_data[
            "youtube_processing_songs"
        ] = processing

    return processing


# =========================================================
# ADMIN MENU
# =========================================================

def admin_menu():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "➕ افزودن آهنگ",
                callback_data="admin_add",
            )
        ],

        [
            InlineKeyboardButton(
                "📊 آمار ربات",
                callback_data="admin_stats",
            ),

            InlineKeyboardButton(
                "🎵 لیست آهنگ‌ها",
                callback_data="admin_songs",
            ),
        ],

        [
            InlineKeyboardButton(
                "ℹ️ راهنمای مدیریت",
                callback_data="admin_help",
            )
        ],

        [
            InlineKeyboardButton(
                "🔙 منوی اصلی",
                callback_data="main_menu",
            )
        ],

    ])


# =========================================================
# ARCHIVE
# =========================================================

def archive_menu(
    page=0
):

    global SONGS

    SONGS = load_songs()

    items = list(
        SONGS.items()
    )

    total = len(
        items
    )

    if total == 0:

        return (

            "📂 آرشیو آهنگ‌ها در حال حاضر خالی است.",

            InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        "🔙 منوی اصلی",
                        callback_data="main_menu",
                    )
                ]

            ]),

        )

    max_page = (
        (total - 1)
        // PAGE_SIZE
    )

    page = max(
        0,
        min(
            page,
            max_page,
        ),
    )

    start = (
        page
        * PAGE_SIZE
    )

    end = (
        start
        + PAGE_SIZE
    )

    page_items = items[
        start:end
    ]

    keyboard = []

    for song_id, info in page_items:

        title = str(
            info.get(
                "title",
                "آهنگ بدون نام",
            )
        )

        keyboard.append([

            InlineKeyboardButton(
                title,
                callback_data=(
                    f"sel_{song_id}"
                ),
            )

        ])

    navigation = []

    if page > 0:

        navigation.append(

            InlineKeyboardButton(
                "⬅️ قبلی",
                callback_data=(
                    f"archive_{page - 1}"
                ),
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
                callback_data=(
                    f"archive_{page + 1}"
                ),
            )

        )

    keyboard.append(
        navigation
    )

    keyboard.append([

        InlineKeyboardButton(
            "🔙 منوی اصلی",
            callback_data="main_menu",
        )

    ])

    text = (

        "🎵 آرشیو آهنگ‌های Majed AI Music\n\n"

        f"🎧 آهنگ‌ها: {total}\n"
        f"📄 صفحه {page + 1} از {max_page + 1}\n\n"

        "👇 آهنگ موردنظرت رو انتخاب کن:"

    )

    return (
        text,
        InlineKeyboardMarkup(
            keyboard
        ),
    )


# =========================================================
# START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not update.message:
        return

    context.user_data[
        "waiting_for_search"
    ] = False

    await update.message.reply_text(

        main_menu_text(),

        reply_markup=main_menu(),

    )


# =========================================================
# ADMIN
# =========================================================

async def admin_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if (
        not update.effective_user
        or not update.message
    ):
        return

    if (
        update.effective_user.id
        != ADMIN_ID
    ):

        await update.message.reply_text(
            "⛔ شما دسترسی مدیریتی ندارید."
        )

        return

    context.user_data[
        "waiting_for_search"
    ] = False

    await update.message.reply_text(

        "🛠 پنل مدیریت Majed AI Music\n\n"
        "از گزینه‌های زیر استفاده کن:",

        reply_markup=admin_menu(),

    )


# =========================================================
# ADD SONG
# =========================================================

async def add_song_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if (
        not update.effective_user
        or not update.message
    ):
        return

    if (
        update.effective_user.id
        != ADMIN_ID
    ):

        await update.message.reply_text(
            "⛔ شما دسترسی مدیریتی ندارید."
        )

        return

    if not context.args:

        await update.message.reply_text(

            "⚠️ روش افزودن آهنگ:\n\n"

            "/add نام آهنگ\n\n"

            "سپس فایل صوتی آهنگ را ارسال کن.\n\n"

            "مثال:\n"
            "/add بزن به سیم آخر"

        )

        return

    title = (
        "🎵 "
        + " ".join(
            context.args
        )
    )

    context.user_data[
        "pending_title"
    ] = title

    await update.message.reply_text(

        f"✅ عنوان ثبت شد:\n\n"
        f"{title}\n\n"

        "🎧 حالا فایل صوتی آهنگ را ارسال کن."

    )


# =========================================================
# CANCEL
# =========================================================

async def cancel_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not update.message:
        return

    context.user_data.pop(
        "pending_title",
        None,
    )

    context.user_data.pop(
        "waiting_for_search",
        None,
    )

    await update.message.reply_text(
        "✅ عملیات لغو شد."
    )


# =========================================================
# DELETE SONG
# =========================================================

async def delete_song_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if (
        not update.effective_user
        or not update.message
    ):
        return

    if (
        update.effective_user.id
        != ADMIN_ID
    ):

        await update.message.reply_text(
            "⛔ شما دسترسی مدیریتی ندارید."
        )

        return

    if not context.args:

        await update.message.reply_text(

            "⚠️ روش حذف آهنگ:\n\n"

            "/delete شناسه_آهنگ\n\n"

            "مثال:\n"
            "/delete 97ef3593"

        )

        return

    song_id = (
        context.args[0]
        .strip()
    )

    global SONGS

    SONGS = load_songs()

    if song_id not in SONGS:

        await update.message.reply_text(
            "❌ چنین آهنگی در آرشیو وجود ندارد."
        )

        return

    title = SONGS[
        song_id
    ].get(
        "title",
        "بدون نام",
    )

    del SONGS[
        song_id
    ]

    save_songs(
        SONGS
    )

    await update.message.reply_text(

        "🗑 آهنگ با موفقیت حذف شد.\n\n"

        f"🎵 {title}\n"
        f"🆔 {song_id}"

    )


# =========================================================
# RENAME SONG
# =========================================================

async def rename_song_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if (
        not update.effective_user
        or not update.message
    ):
        return

    if (
        update.effective_user.id
        != ADMIN_ID
    ):

        await update.message.reply_text(
            "⛔ شما دسترسی مدیریتی ندارید."
        )

        return

    if len(context.args) < 2:

        await update.message.reply_text(

            "⚠️ روش تغییر نام:\n\n"

            "/rename شناسه نام جدید\n\n"

            "مثال:\n"
            "/rename 97ef3593 آهنگ جدید من"

        )

        return

    song_id = context.args[
        0
    ]

    new_title = (
        "🎵 "
        + " ".join(
            context.args[1:]
        )
    )

    global SONGS

    SONGS = load_songs()

    if song_id not in SONGS:

        await update.message.reply_text(
            "❌ چنین آهنگی وجود ندارد."
        )

        return

    old_title = SONGS[
        song_id
    ].get(
        "title",
        "بدون نام",
    )

    SONGS[
        song_id
    ][
        "title"
    ] = new_title

    save_songs(
        SONGS
    )

    await update.message.reply_text(

        "✏️ نام آهنگ تغییر کرد.\n\n"

        f"قبلی:\n{old_title}\n\n"

        f"جدید:\n{new_title}"

    )


# =========================================================
# STATS
# =========================================================

async def stats(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if (
        not update.effective_user
        or not update.message
    ):
        return

    if (
        update.effective_user.id
        != ADMIN_ID
    ):

        await update.message.reply_text(
            "⛔ شما دسترسی مدیریتی ندارید."
        )

        return

    global SONGS

    SONGS = load_songs()

    total_songs = len(
        SONGS
    )

    total_downloads = (
        get_total_downloads()
    )

    sorted_songs = sorted(

        SONGS.items(),

        key=lambda item: int(
            item[1].get(
                "downloads",
                0,
            )
        ),

        reverse=True,

    )

    lines = [

        "📊 گزارش کامل Majed AI Music",
        "",
        f"🎧 تعداد آهنگ‌ها: {total_songs}",
        f"📥 مجموع دانلودها: {total_downloads}",
        "",
        "🔥 پربازدیدترین آهنگ‌ها:",
        "",
    ]

    for index, (
        _,
        info
    ) in enumerate(

        sorted_songs[:10],

        start=1,

    ):

        title = str(
            info.get(
                "title",
                "بدون نام",
            )
        )

        try:

            downloads = int(
                info.get(
                    "downloads",
                    0,
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            downloads = 0

        lines.append(
            f"{index}. {title} — {downloads} دانلود"
        )

    await update.message.reply_text(
        "\n".join(
            lines
        )
    )


# =========================================================
# HANDLE MESSAGE
# =========================================================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    global SONGS

    if (
        not update.message
        or not update.effective_user
    ):
        return

    user_id = (
        update.effective_user.id
    )

    # =====================================================
    # USER SEARCH
    # =====================================================

    if user_id != ADMIN_ID:

        if context.user_data.get(
            "waiting_for_search"
        ):

            context.user_data[
                "waiting_for_search"
            ] = False

            query_text = (
                update.message.text
                or ""
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
                        "",
                    )
                )

                if (
                    query_text.casefold()
                    in title.casefold()
                ):

                    matched.append(
                        (
                            song_id,
                            info,
                        )
                    )

            keyboard = []

            for song_id, info in matched[:10]:

                keyboard.append([

                    InlineKeyboardButton(

                        str(
                            info.get(
                                "title",
                                "آهنگ",
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

                    f"🎵 تعداد نتایج: "
                    f"{len(matched)}\n\n"

                    "👇 آهنگ موردنظرت رو انتخاب کن:"

                )

            else:

                text = (

                    f"❌ آهنگی برای "
                    f"«{query_text}» پیدا نشد."

                )

            await update.message.reply_text(

                text,

                reply_markup=(
                    InlineKeyboardMarkup(
                        keyboard
                    )
                ),

            )

        return

    # =====================================================
    # ADMIN MEDIA
    # =====================================================

    msg = update.message

    file_id = None

    if msg.audio:

        file_id = (
            msg.audio.file_id
        )

    elif msg.voice:

        file_id = (
            msg.voice.file_id
        )

    elif msg.document:

        file_id = (
            msg.document.file_id
        )

    if not file_id:
        return

    if (
        "pending_title"
        not in context.user_data
    ):

        await msg.reply_text(

            "📁 فایل دریافت شد.\n\n"

            "برای ثبت آهنگ ابتدا بنویس:\n\n"

            "/add نام آهنگ"

        )

        return

    title = context.user_data.pop(
        "pending_title"
    )

    SONGS = load_songs()

    song_id = uuid.uuid4().hex[:8]

    SONGS[
        song_id
    ] = {

        "title": title,

        "file_id": file_id,

        "downloads": 0,

    }

    save_songs(
        SONGS
    )

    await msg.reply_text(

        "🎉 آهنگ با موفقیت اضافه شد!\n\n"

        f"🎵 {title}\n"
        f"🆔 شناسه: {song_id}\n\n"

        "✅ آهنگ اکنون داخل آرشیو قرار گرفت."

    )


# =========================================================
# SEND SONG
# =========================================================

async def send_song(
    query,
    context,
    song_id,
):

    global SONGS

    SONGS = load_songs()

    if song_id not in SONGS:

        await query.message.edit_text(
            "❌ آهنگ پیدا نشد."
        )

        return

    song = SONGS[
        song_id
    ]

    file_id = song.get(
        "file_id"
    )

    if not file_id:

        await query.message.edit_text(

            "❌ فایل این آهنگ ثبت نشده است.\n\n"
            "لطفاً به ادمین اطلاع دهید."

        )

        return

    chat_id = (
        query.message.chat_id
    )

    await query.message.edit_text(

        f"⏳ در حال ارسال "
        f"{song['title']} ..."

    )

    caption = (

        f"🎵 {song['title']}\n\n"

        f"🔗 کانال رسمی ما: "
        f"{TELEGRAM_CHANNEL}"

    )

    sent = False

    # =====================================================
    # AUDIO
    # =====================================================

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

    # =====================================================
    # DOCUMENT FALLBACK
    # =====================================================

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

    # =====================================================
    # SUCCESS
    # =====================================================

    if sent:

        try:

            current_downloads = int(
                SONGS[
                    song_id
                ].get(
                    "downloads",
                    0,
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            current_downloads = 0

        SONGS[
            song_id
        ][
            "downloads"
        ] = (
            current_downloads
            + 1
        )

        save_songs(
            SONGS
        )

        await context.bot.send_message(

            chat_id=chat_id,

            text=(

                "🎧 آهنگ با موفقیت ارسال شد! ❤️\n\n"

                "برای دریافت آهنگ‌های دیگر "
                "از آرشیو استفاده کن."

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
                        "🔥 جدیدترین‌ها",
                        callback_data="latest_songs",
                    )
                ],

                [
                    InlineKeyboardButton(
                        "🏠 منوی اصلی",
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

                "لطفاً چند لحظه بعد دوباره تلاش کن."

            ),

        )


# =========================================================
# BUTTON HANDLER
# =========================================================

async def button(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    global SONGS

    query = update.callback_query

    if not query:
        return

    try:

        await query.answer()

    except Exception:

        pass

    SONGS = load_songs()

    data = (
        query.data
        or ""
    )

    user_id = (
        query.from_user.id
    )

    # =====================================================
    # NOOP
    # =====================================================

    if data == "noop":
        return

    # =====================================================
    # MAIN MENU
    # =====================================================

    if data == "main_menu":

        context.user_data[
            "waiting_for_search"
        ] = False

        await query.message.edit_text(

            main_menu_text(),

            reply_markup=main_menu(),

        )

        return

    # =====================================================
    # ADMIN ADD
    # =====================================================

    if data == "admin_add":

        if user_id != ADMIN_ID:
            return

        await query.message.edit_text(

            "➕ افزودن آهنگ\n\n"

            "ابتدا این دستور را ارسال کن:\n\n"

            "/add نام آهنگ\n\n"

            "سپس فایل صوتی آهنگ را بفرست.",

            reply_markup=InlineKeyboardMarkup([

                [

                    InlineKeyboardButton(
                        "🔙 پنل مدیریت",
                        callback_data="admin_menu",
                    )

                ]

            ]),

        )

        return

    # =====================================================
    # ADMIN MENU
    # =====================================================

    if data == "admin_menu":

        if user_id != ADMIN_ID:
            return

        await query.message.edit_text(

            "🛠 پنل مدیریت Majed AI Music\n\n"

            "مدیریت آهنگ‌ها و مشاهده آمار:",

            reply_markup=admin_menu(),

        )

        return

    # =====================================================
    # ADMIN STATS
    # =====================================================

    if data == "admin_stats":

        if user_id != ADMIN_ID:
            return

        SONGS = load_songs()

        top = sorted(

            SONGS.values(),

            key=lambda x: int(
                x.get(
                    "downloads",
                    0,
                )
            ),

            reverse=True,

        )

        lines = [

            "📊 آمار ربات",
            "",
            f"🎧 تعداد آهنگ‌ها: {len(SONGS)}",
            f"📥 مجموع دانلودها: {get_total_downloads()}",
            "",
            "🔥 پربازدیدترین‌ها:",
            "",
        ]

        for index, info in enumerate(
            top[:5],
            start=1,
        ):

            try:

                downloads = int(
                    info.get(
                        "downloads",
                        0,
                    )
                )

            except (
                TypeError,
                ValueError,
            ):

                downloads = 0

            lines.append(

                f"{index}. "
                f"{info.get('title', 'بدون نام')} "
                f"— "
                f"{downloads}"

            )

        await query.message.edit_text(

            "\n".join(
                lines
            ),

            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        "🔄 بروزرسانی",
                        callback_data="admin_stats",
                    )
                ],

                [
                    InlineKeyboardButton(
                        "🔙 پنل مدیریت",
                        callback_data="admin_menu",
                    )
                ],

            ]),

        )

        return

    # =====================================================
    # ADMIN SONG LIST
    # =====================================================

    if data == "admin_songs":

        if user_id != ADMIN_ID:
            return

        SONGS = load_songs()

        if not SONGS:

            text = (
                "📂 هنوز هیچ آهنگی "
                "در آرشیو وجود ندارد."
            )

        else:

            lines = [
                "🎵 لیست آهنگ‌های ثبت‌شده:",
                "",
            ]

            for song_id, info in SONGS.items():

                title = info.get(
                    "title",
                    "بدون نام",
                )

                try:

                    downloads = int(
                        info.get(
                            "downloads",
                            0,
                        )
                    )

                except (
                    TypeError,
                    ValueError,
                ):

                    downloads = 0

                lines.append(

                    f"🎵 {title}\n"
                    f"🆔 {song_id} | "
                    f"📥 {downloads}\n"

                )

            text = "\n".join(
                lines
            )

        await query.message.edit_text(

            text,

            reply_markup=InlineKeyboardMarkup([

                [
                    InlineKeyboardButton(
                        "🔙 پنل مدیریت",
                        callback_data="admin_menu",
                    )
                ]

            ]),

        )

        return

    # =====================================================
    # ADMIN HELP
    # =====================================================

    if data == "admin_help":

        if user_id != ADMIN_ID:
            return

        text = (

            "ℹ️ راهنمای مدیریت\n\n"

            "➕ افزودن آهنگ:\n"
            "/add نام آهنگ\n"
            "سپس فایل صوتی را ارسال کن.\n\n"

            "🗑 حذف آهنگ:\n"
            "/delete شناسه\n\n"

            "✏️ تغییر نام:\n"
            "/rename شناسه نام جدید\n\n"

            "📊 آمار:\n"
            "/stats\n\n"

            "❌ لغو عملیات:\n"
            "/cancel"

        )

        await query.message.edit_text(

            text,

            reply_markup=InlineKeyboardMarkup([

                [

                    InlineKeyboardButton(
                        "🔙 پنل مدیریت",
                        callback_data="admin_menu",
                    )

                ]

            ]),

        )

        return

    # =====================================================
    # ARCHIVE
    # =====================================================

    if data.startswith(
        "archive_"
    ):

        try:

            page = int(
                data.split(
                    "_",
                    1,
                )[1]
            )

        except ValueError:

            page = 0

        text, markup = (
            archive_menu(
                page
            )
        )

        await query.message.edit_text(

            text,

            reply_markup=markup,

        )

        return

    # =====================================================
    # SEARCH
    # =====================================================

    if data == "search_start":

        context.user_data[
            "waiting_for_search"
        ] = True

        await query.message.edit_text(

            "🔎 جستجوی آهنگ‌ها\n\n"

            "نام یا بخشی از نام آهنگ را "
            "همینجا ارسال کن:",

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

    # =====================================================
    # LATEST SONGS
    # =====================================================

    if data == "latest_songs":

        items = list(
            SONGS.items()
        )

        latest = (
            items[-10:][::-1]
        )

        keyboard = []

        for song_id, info in latest:

            keyboard.append([

                InlineKeyboardButton(

                    str(
                        info.get(
                            "title",
                            "آهنگ",
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

                "🔥 جدیدترین آهنگ‌های "
                "Majed AI Music\n\n"

                "👇 آهنگ موردنظرت رو انتخاب کن:"

            )

        else:

            text = (
                "🔥 هنوز آهنگی اضافه نشده است."
            )

        await query.message.edit_text(

            text,

            reply_markup=InlineKeyboardMarkup(
                keyboard
            ),

        )

        return

    # =====================================================
    # SELECT SONG
    # =====================================================

    if data.startswith(
        "sel_"
    ):

        song_id = data.split(
            "_",
            1,
        )[1]

        if song_id not in SONGS:

            await query.message.edit_text(

                "❌ این آهنگ دیگر "
                "در آرشیو موجود نیست.",

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

        song = SONGS[
            song_id
        ]

        # =================================================
        # ALREADY CONFIRMED
        # =================================================

        if is_song_confirmed(
            context,
            song_id,
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
                        "🔴 حمایت دوباره "
                        "در یوتیوب ❤️",
                        url=YOUTUBE_URL,
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

                f"🎵 {song['title']}\n\n"

                "❤️ دسترسی دانلود این آهنگ فعال است.\n\n"

                "برای دریافت فایل روی دانلود بزن.",

                reply_markup=keyboard,

            )

            return

        # =================================================
        # NEW SONG
        # =================================================

        await query.message.edit_text(

            youtube_gate_text(
                song
            ),

            reply_markup=(
                youtube_gate_keyboard(
                    song_id
                )
            ),

        )

        return

    # =====================================================
    # YOUTUBE CONFIRM
    # =====================================================

    if data.startswith(
        "youtube_confirm_"
    ):

        song_id = data.split(
            "_",
            2,
        )[2]

        if song_id not in SONGS:

            await query.message.edit_text(
                "❌ آهنگ پیدا نشد."
            )

            return

        # =================================================
        # ALREADY CONFIRMED
        # =================================================

        if is_song_confirmed(
            context,
            song_id,
        ):

            await query.message.edit_text(

                "🎧 این آهنگ قبلاً برای شما فعال شده.\n\n"
                "در حال ارسال آهنگ..."

            )

            await send_song(

                query,
                context,
                song_id,

            )

            return

        # =================================================
        # PROCESSING LOCK
        # =================================================

        processing = (
            get_processing_songs(
                context
            )
        )

        if song_id in processing:

            await query.answer(
                "⏳ درخواست شما در حال پردازش است...",
                show_alert=False,
            )

            return

        # =================================================
        # COUNT CLICK
        # =================================================

        attempts = (
            increment_song_attempts(
                context,
                song_id,
            )
        )

        # =================================================
        # CLICK 1
        # =================================================

        if attempts == 1:

            await query.message.edit_text(

                youtube_second_warning_text(
                    SONGS[song_id]
                ),

                reply_markup=(
                    youtube_gate_keyboard(
                        song_id
                    )
                ),

            )

            return

        # =================================================
        # CLICK 2
        # =================================================

        if attempts == 2:

            await query.message.edit_text(

                youtube_second_warning_text(
                    SONGS[song_id]
                ),

                reply_markup=(
                    youtube_gate_keyboard(
                        song_id
                    )
                ),

            )

            return

        # =================================================
        # CLICK 3
        # =================================================

        processing.add(
            song_id
        )

        try:

            await query.message.edit_text(

                "⏳ در حال بررسی عضویت...\n\n"
                "لطفاً چند لحظه صبر کن."

            )

            await asyncio.sleep(
                3
            )

            # -------------------------------------------------
            # HONOR SYSTEM
            # -------------------------------------------------
            #
            # عضویت YouTube در این نسخه واقعاً از API
            # بررسی نمی‌شود.
            #
            # -------------------------------------------------

            confirm_song(
                context,
                song_id,
            )

            await query.message.edit_text(

                "🎉 ممنون از حمایتت ❤️\n\n"

                "🎧 آهنگ در حال ارسال است..."

            )

            await send_song(

                query,
                context,
                song_id,

            )

        except Exception:

            logger.exception(
                "YouTube confirmation flow failed"
            )

            await query.message.edit_text(

                "❌ مشکلی در پردازش درخواست پیش آمد.\n\n"
                "لطفاً دوباره تلاش کن."

            )

        finally:

            processing.discard(
                song_id
            )

        return

    # =====================================================
    # DOWNLOAD
    # =====================================================

    if data.startswith(
        "download_"
    ):

        song_id = data.split(
            "_",
            1,
        )[1]

        if song_id not in SONGS:

            await query.message.edit_text(
                "❌ آهنگ پیدا نشد."
            )

            return

        if not is_song_confirmed(
            context,
            song_id,
        ):

            song = SONGS[
                song_id
            ]

            await query.message.edit_text(

                youtube_gate_text(
                    song
                ),

                reply_markup=(
                    youtube_gate_keyboard(
                        song_id
                    )
                ),

            )

            return

        await send_song(

            query,
            context,
            song_id,

        )

        return


# =========================================================
# HANDLERS
# =========================================================

telegram_app.add_handler(
    CommandHandler(
        "start",
        start,
    )
)

telegram_app.add_handler(
    CommandHandler(
        "admin",
        admin_command,
    )
)

telegram_app.add_handler(
    CommandHandler(
        "add",
        add_song_command,
    )
)

telegram_app.add_handler(
    CommandHandler(
        "delete",
        delete_song_command,
    )
)

telegram_app.add_handler(
    CommandHandler(
        "rename",
        rename_song_command,
    )
)

telegram_app.add_handler(
    CommandHandler(
        "stats",
        stats,
    )
)

telegram_app.add_handler(
    CommandHandler(
        "cancel",
        cancel_command,
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
        button,
    )
)


# =========================================================
# BOT LOOP
# =========================================================

bot_loop = asyncio.new_event_loop()

bot_thread = None

bot_start_error = None

bot_started_at = None

webhook_ready = False


async def setup_bot():

    global bot_start_error
    global bot_started_at
    global webhook_ready

    logger.info(
        "Initializing Telegram application..."
    )

    # -----------------------------------------------------
    # INITIALIZE
    # -----------------------------------------------------

    await telegram_app.initialize()

    # -----------------------------------------------------
    # START APPLICATION
    # -----------------------------------------------------

    await telegram_app.start()

    logger.info(
        "Telegram application started."
    )

    # -----------------------------------------------------
    # WEBHOOK
    # -----------------------------------------------------

    if not WEBHOOK_URL:

        raise RuntimeError(

            "Webhook URL is not available. "
            "RENDER_EXTERNAL_URL or WEBHOOK_URL "
            "environment variable is required."

        )

    logger.info(
        "Setting Telegram webhook..."
    )

    webhook_kwargs = {

        "url": WEBHOOK_URL,

        # پیام‌های معلق حذف نمی‌شوند
        # تا بعد از restart از دست نروند
        "drop_pending_updates": False,

        "allowed_updates": Update.ALL_TYPES,

    }

    if WEBHOOK_SECRET:

        webhook_kwargs[
            "secret_token"
        ] = WEBHOOK_SECRET

    await telegram_app.bot.set_webhook(
        **webhook_kwargs
    )

    webhook_ready = True

    bot_started_at = time.time()

    bot_start_error = None

    logger.info(
        "========================================"
    )

    logger.info(
        "Majed AI Music Bot is RUNNING"
    )

    logger.info(
        "Telegram WEBHOOK is ACTIVE"
    )

    logger.info(
        "Webhook URL: %s",
        WEBHOOK_URL,
    )

    logger.info(
        "========================================"
    )


def run_bot():

    global bot_start_error

    asyncio.set_event_loop(
        bot_loop
    )

    retry_delay = 10

    while True:

        try:

            bot_loop.run_until_complete(
                setup_bot()
            )

            # -------------------------------------------------
            # KEEP ASYNC APPLICATION ALIVE
            # -------------------------------------------------

            bot_loop.run_forever()

            break

        except Exception as exc:

            bot_start_error = repr(
                exc
            )

            logger.exception(
                "BOT START FAILED"
            )

            logger.error(
                "Retrying in %s seconds...",
                retry_delay,
            )

            time.sleep(
                retry_delay
            )

            retry_delay = min(
                retry_delay * 2,
                60,
            )


# =========================================================
# START BOT THREAD
# =========================================================

bot_thread = threading.Thread(

    target=run_bot,

    name="telegram-bot",

    daemon=True,

)

bot_thread.start()


# =========================================================
# TELEGRAM WEBHOOK ROUTE
# =========================================================

@app.post("/telegram")
def telegram_webhook():

    # -----------------------------------------------------
    # OPTIONAL SECRET CHECK
    # -----------------------------------------------------

    if WEBHOOK_SECRET:

        received_secret = request.headers.get(
            "X-Telegram-Bot-Api-Secret-Token"
        )

        if received_secret != WEBHOOK_SECRET:

            logger.warning(
                "Rejected Telegram webhook request: "
                "invalid secret."
            )

            return (
                jsonify({
                    "ok": False,
                    "error": "Unauthorized",
                }),
                403,
            )

    # -----------------------------------------------------
    # GET JSON
    # -----------------------------------------------------

    try:

        data = request.get_json(
            force=True,
            silent=False,
        )

    except Exception:

        logger.exception(
            "Could not parse Telegram webhook JSON."
        )

        return (
            jsonify({
                "ok": False,
            }),
            400,
        )

    if not data:

        return (
            jsonify({
                "ok": False,
            }),
            400,
        )

    # -----------------------------------------------------
    # CONVERT TO PTB UPDATE
    # -----------------------------------------------------

    try:

        update = Update.de_json(
            data,
            telegram_app.bot,
        )

    except Exception:

        logger.exception(
            "Could not create Telegram Update."
        )

        return (
            jsonify({
                "ok": False,
            }),
            400,
        )

    # -----------------------------------------------------
    # PUT UPDATE INTO PTB QUEUE
    # -----------------------------------------------------
    #
    # چون Webhook است، دیگر getUpdates / Polling نداریم.
    #
    # -----------------------------------------------------

    try:

        bot_loop.call_soon_threadsafe(

            telegram_app.update_queue.put_nowait,

            update,

        )

    except Exception:

        logger.exception(
            "Could not queue Telegram update."
        )

        return (
            jsonify({
                "ok": False,
            }),
            500,
        )

    # -----------------------------------------------------
    # RESPOND IMMEDIATELY
    # -----------------------------------------------------

    return (
        jsonify({
            "ok": True,
        }),
        200,
    )


# =========================================================
# HOME
# =========================================================

@app.get("/")
def index():

    return (

        "Majed AI Music Bot is running! "

        "Webhook mode is active.",

        200,

    )


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
def health():

    telegram_running = False

    try:

        telegram_running = bool(
            telegram_app.running
        )

    except Exception:

        telegram_running = False

    uptime = None

    if bot_started_at:

        uptime = int(
            time.time()
            - bot_started_at
        )

    return jsonify({

        "status":
            "ok",

        "service":
            "Majed AI Music Bot",

        "mode":
            "webhook",

        "webhook_url":
            WEBHOOK_URL,

        "webhook_ready":
            webhook_ready,

        "telegram_running":
            telegram_running,

        "bot_thread_alive":
            bot_thread.is_alive(),

        "bot_start_error":
            bot_start_error,

        "uptime_seconds":
            uptime,

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
                10000,
            )
        ),

    )
