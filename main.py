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
    """
    Load songs from songs_db.json.
    """

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

        except Exception:
            pass

    return total


def get_total_songs():

    global SONGS

    SONGS = load_songs()

    return len(SONGS)


# =========================================================
# MAIN MENU
# =========================================================

def main_menu():

    total_songs = get_total_songs()
    total_downloads = get_total_downloads()

    return InlineKeyboardMarkup([

        # مستقیم به یوتیوب
        [
            InlineKeyboardButton(
                "🔴 حمایت از ما در یوتیوب ❤️",
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
                "🔎 جستجوی آهنگ",
                callback_data="search_start",
            ),
        ],

        [
            InlineKeyboardButton(
                f"🎧 {total_songs} آهنگ",
                callback_data="archive_0",
            ),

            InlineKeyboardButton(
                f"📥 {total_downloads} دانلود",
                callback_data="noop",
            ),
        ],

    ])


def main_menu_text():

    total_songs = get_total_songs()
    total_downloads = get_total_downloads()

    return (
        "✨ به Majed AI Music خوش آمدید\n\n"

        "🎧 آرشیو اختصاصی موسیقی\n"
        "🎵 جدیدترین آهنگ‌ها و موزیک‌های ما\n\n"

        f"🎼 تعداد آهنگ‌ها: {total_songs}\n"
        f"📥 مجموع دانلودها: {total_downloads}\n\n"

        "❤️ برای دریافت آهنگ، وارد آرشیو شوید.\n"
        "اگر دوست داری از ما حمایت کنی، "
        "می‌تونی کانال یوتیوب ما رو Subscribe کنی."
    )


# =========================================================
# YOUTUBE SUBSCRIBE GATE
# =========================================================

def youtube_gate_keyboard(song_id):

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "🔴 سابسکرایب در یوتیوب ❤️",
                url=YOUTUBE_URL,
            )
        ],

        [
            InlineKeyboardButton(
                "✅ سابسکرایب کردم — دریافت آهنگ",
                callback_data=f"youtube_confirm_{song_id}",
            )
        ],

        [
            InlineKeyboardButton(
                "🔙 انتخاب آهنگ دیگر",
                callback_data="archive_0",
            )
        ],

    ])


def youtube_gate_text(song):

    return (
        "❤️ یک حمایت کوچک برای ادامه\n\n"

        f"🎵 {song['title']}\n\n"

        "اگر از موسیقی‌های Majed AI Music خوشت میاد، "
        "لطفاً با یک Subscribe در یوتیوب از ما حمایت کن. 🎧\n\n"

        "🔥 حمایت تو کمک می‌کنه موزیک‌های جدید بیشتری "
        "تولید کنیم.\n\n"

        "👇 اول روی دکمه قرمز بزن و در یوتیوب Subscribe کن.\n"
        "بعد برگرد و روی «سابسکرایب کردم — دریافت آهنگ» بزن."
    )


def youtube_warning_keyboard(song_id):

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "🔴 دوباره رفتن به یوتیوب ❤️",
                url=YOUTUBE_URL,
            )
        ],

        [
            InlineKeyboardButton(
                "✅ سابسکرایب کردم — دریافت آهنگ",
                callback_data=f"youtube_confirm_{song_id}",
            )
        ],

        [
            InlineKeyboardButton(
                "🔙 انتخاب آهنگ دیگر",
                callback_data="archive_0",
            )
        ],

    ])


def youtube_warning_text(song):

    return (
        "⚠️ هنوز یک مرحله باقی مانده!\n\n"

        f"🎵 آهنگ: {song['title']}\n\n"

        "برای دریافت این آهنگ، لطفاً ابتدا در یوتیوب "
        "کانال Majed AI Music را Subscribe کن ❤️\n\n"

        "اگر هنوز Subscribe نکردی، روی دکمه زیر بزن.\n"
        "بعد دوباره «سابسکرایب کردم — دریافت آهنگ» را بزن."
    )


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

def archive_menu(page=0):

    global SONGS

    SONGS = load_songs()

    items = list(SONGS.items())

    total = len(items)

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


    max_page = (total - 1) // PAGE_SIZE

    page = max(
        0,
        min(
            page,
            max_page,
        ),
    )


    start = page * PAGE_SIZE
    end = start + PAGE_SIZE

    page_items = items[start:end]

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

        "🎵 آرشیو آهنگ‌های Majed AI Music\n\n"

        f"🎧 تعداد کل آهنگ‌ها: {total}\n"
        f"📄 صفحه {page + 1} از {max_page + 1}\n\n"

        "👇 آهنگ موردنظر را انتخاب کنید:"
    )


    return (
        text,
        InlineKeyboardMarkup(keyboard),
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

    context.user_data["waiting_for_search"] = False

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

    if not update.effective_user:
        return

    if update.effective_user.id != ADMIN_ID:

        await update.message.reply_text(
            "⛔ شما دسترسی مدیریتی ندارید."
        )

        return

    context.user_data["waiting_for_search"] = False

    await update.message.reply_text(

        "🛠 پنل مدیریت Majed AI Music\n\n"
        "از گزینه‌های زیر استفاده کنید:",

        reply_markup=admin_menu(),

    )


# =========================================================
# ADD SONG
# =========================================================

async def add_song_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
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

            "⚠️ روش افزودن آهنگ:\n\n"

            "/add نام آهنگ\n\n"

            "سپس فایل صوتی آهنگ را ارسال کنید.\n\n"

            "مثال:\n"

            "/add بزن به سیم آخر"

        )

        return


    title = "🎵 " + " ".join(
        context.args
    )


    context.user_data[
        "pending_title"
    ] = title


    await update.message.reply_text(

        f"✅ عنوان ثبت شد:\n\n"
        f"{title}\n\n"

        "🎧 حالا فایل صوتی آهنگ را ارسال کنید."

    )


# =========================================================
# CANCEL
# =========================================================

async def cancel_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not update.effective_user:
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

    if not update.effective_user:
        return


    if update.effective_user.id != ADMIN_ID:

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


    song_id = context.args[0].strip()


    global SONGS

    SONGS = load_songs()


    if song_id not in SONGS:

        await update.message.reply_text(
            "❌ چنین آهنگی در آرشیو وجود ندارد."
        )

        return


    title = SONGS[song_id].get(
        "title",
        "بدون نام",
    )


    del SONGS[song_id]

    save_songs(SONGS)


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

    if not update.effective_user:
        return


    if update.effective_user.id != ADMIN_ID:

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


    song_id = context.args[0]

    new_title = "🎵 " + " ".join(
        context.args[1:]
    )


    global SONGS

    SONGS = load_songs()


    if song_id not in SONGS:

        await update.message.reply_text(
            "❌ چنین آهنگی وجود ندارد."
        )

        return


    old_title = SONGS[song_id].get(
        "title",
        "بدون نام",
    )


    SONGS[song_id]["title"] = new_title

    save_songs(SONGS)


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

    total_downloads = get_total_downloads()


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

        f"🎵 تعداد آهنگ‌ها: {total_songs}",

        f"📥 مجموع دانلودها: {total_downloads}",

        "",

        "🔥 پربازدیدترین آهنگ‌ها:",

    ]


    for index, (song_id, info) in enumerate(
        sorted_songs[:10],
        start=1,
    ):

        title = str(
            info.get(
                "title",
                "بدون نام",
            )
        )

        downloads = int(
            info.get(
                "downloads",
                0,
            )
        )


        lines.append(

            f"{index}. {title} — "
            f"{downloads} دانلود"

        )


    await update.message.reply_text(
        "\n".join(lines)
    )


# =========================================================
# HANDLE MESSAGE
# =========================================================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    global SONGS


    if not update.message:
        return


    if not update.effective_user:
        return


    user_id = update.effective_user.id


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
                        "",
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

                    f"🎵 تعداد نتایج: {len(matched)}\n\n"

                    "👇 آهنگ موردنظر را انتخاب کنید:"
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


    # =====================================================
    # ADMIN MEDIA
    # =====================================================

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


    if (
        "pending_title"
        not in context.user_data
    ):

        await msg.reply_text(

            "📁 فایل دریافت شد.\n\n"

            "برای ثبت آهنگ ابتدا بنویسید:\n\n"

            "/add نام آهنگ"

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


    song = SONGS[song_id]

    file_id = song.get("file_id")


    if not file_id:

        await query.message.edit_text(

            "❌ فایل این آهنگ ثبت نشده است.\n\n"
            "لطفاً به ادمین اطلاع دهید."

        )

        return


    chat_id = query.message.chat_id


    await query.message.edit_text(

        f"⏳ در حال ارسال {song['title']} ..."

    )


    caption = (

        f"🎵 {song['title']}\n\n"

        f"🔗 کانال رسمی ما: {TELEGRAM_CHANNEL}"

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

        SONGS[song_id]["downloads"] = (

            int(
                SONGS[song_id].get(
                    "downloads",
                    0,
                )
            )
            + 1

        )


        save_songs(SONGS)


        await context.bot.send_message(

            chat_id=chat_id,

            text=(

                "🎧 آهنگ با موفقیت ارسال شد! ❤️\n\n"

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

                "لطفاً به ادمین اطلاع دهید."

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


    await query.answer()


    SONGS = load_songs()


    data = query.data

    user_id = query.from_user.id


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

            "ابتدا این دستور را ارسال کنید:\n\n"

            "/add نام آهنگ\n\n"

            "سپس فایل صوتی آهنگ را بفرستید.",

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


        total_songs = len(SONGS)

        total_downloads = get_total_downloads()


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

            f"🎵 تعداد آهنگ‌ها: {total_songs}",

            f"📥 مجموع دانلودها: {total_downloads}",

            "",

            "🔥 پربازدیدترین‌ها:",

        ]


        for index, info in enumerate(
            top[:5],
            start=1,
        ):

            lines.append(

                f"{index}. "
                f"{info.get('title', 'بدون نام')} "
                f"— {int(info.get('downloads', 0))}"

            )


        await query.message.edit_text(

            "\n".join(lines),

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
                "📂 هنوز هیچ آهنگی در آرشیو وجود ندارد."
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

                downloads = int(
                    info.get(
                        "downloads",
                        0,
                    )
                )


                lines.append(

                    f"🎵 {title}\n"
                    f"🆔 {song_id} | 📥 {downloads}\n"

                )


            text = "\n".join(lines)


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
            "سپس فایل صوتی را ارسال کنید.\n\n"

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

    if data.startswith("archive_"):

        try:

            page = int(
                data.split(
                    "_",
                    1,
                )[1]
            )

        except ValueError:

            page = 0


        text, markup = archive_menu(page)


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

            "🔎 جستجوی آهنگ\n\n"

            "نام یا بخشی از نام آهنگ را "
            "همینجا ارسال کنید:",

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


        latest = items[-10:][::-1]


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

                "🔥 جدیدترین آهنگ‌های Majed AI Music\n\n"

                "👇 آهنگ موردنظر را انتخاب کنید:"

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

    if data.startswith("sel_"):

        song_id = data.split(
            "_",
            1,
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


        # =================================================
        # USER ALREADY PASSED SUBSCRIBE GATE
        # =================================================

        if context.user_data.get(
            "youtube_confirmed",
            False,
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
                        "🔴 حمایت دوباره در یوتیوب ❤️",
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

                "❤️ دسترسی دانلود شما فعال است.\n\n"

                "برای دریافت فایل روی دانلود بزنید.",

                reply_markup=keyboard,

            )

            return


        # =================================================
        # FIRST TIME
        # =================================================

        await query.message.edit_text(

            youtube_gate_text(song),

            reply_markup=youtube_gate_keyboard(song_id),

        )

        return


    # =====================================================
    # YOUTUBE CONFIRM
    # =====================================================

    if data.startswith("youtube_confirm_"):

        song_id = data.split(
            "_",
            2,
        )[2]


        if song_id not in SONGS:

            await query.message.edit_text(
                "❌ آهنگ پیدا نشد."
            )

            return


        song = SONGS[song_id]


        # -------------------------------------------------
        # Honor-system confirmation
        # -------------------------------------------------

        attempts = int(
            context.user_data.get(
                "youtube_attempts",
                0,
            )
        )


        # =================================================
        # FIRST CLICK
        # =================================================

        if attempts == 0:

            context.user_data[
                "youtube_attempts"
            ] = 1


            await query.message.edit_text(

                youtube_warning_text(song),

                reply_markup=(
                    youtube_warning_keyboard(
                        song_id
                    )
                ),

            )

            return


        # =================================================
        # SECOND CLICK
        # =================================================

        context.user_data[
            "youtube_attempts"
        ] = attempts + 1


        context.user_data[
            "youtube_confirmed"
        ] = True


        await query.message.edit_text(

            "🎉 ممنون از حمایتت ❤️\n\n"

            "آهنگ در حال ارسال است... 🎧"

        )


        # مستقیم آهنگ را ارسال کن
        await send_song(
            query,
            context,
            song_id,
        )

        return


    # =====================================================
    # DOWNLOAD
    # =====================================================

    if data.startswith("download_"):

        song_id = data.split(
            "_",
            1,
        )[1]


        if not context.user_data.get(
            "youtube_confirmed",
            False,
        ):

            if song_id not in SONGS:

                await query.message.edit_text(
                    "❌ آهنگ پیدا نشد."
                )

                return


            song = SONGS[song_id]


            await query.message.edit_text(

                youtube_gate_text(song),

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


        # -------------------------------------------------
        # Remove old webhook
        # -------------------------------------------------

        await telegram_app.bot.delete_webhook(
            drop_pending_updates=True
        )


        # -------------------------------------------------
        # Start application
        # -------------------------------------------------

        await telegram_app.start()


        if telegram_app.updater is None:

            raise RuntimeError(
                "Telegram updater is unavailable."
            )


        # -------------------------------------------------
        # Start polling
        # -------------------------------------------------

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
        200,
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
                10000,
            )
        ),

    )
