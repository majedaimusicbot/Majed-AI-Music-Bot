import os
import logging
import json
import uuid
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# تنظیمات لاگینگ
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("خطا: متغیر محیطی BOT_TOKEN تنظیم نشده است.")

admin_id_env = os.environ.get("ADMIN_ID")
if not admin_id_env:
    raise ValueError("خطا: متغیر محیطی ADMIN_ID تنظیم نشده است.")
ADMIN_ID = int(admin_id_env)

# آدرس رندر شما
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")

YOUTUBE_URL = "https://www.youtube.com/@DeepHouse_Farsi?sub_confirmation=1"
DB_FILE = "songs_db.json"
PAGE_SIZE = 10

app = Flask(__name__)

def load_songs():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return {}
                return json.loads(content)
        except Exception as e:
            logging.error(f"Error reading {DB_FILE}: {e}")
    return {}

def save_songs(songs):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(songs, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Error saving to {DB_FILE}: {e}")

SONGS = load_songs()

def get_main_menu_markup():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❤️ عضویت در یوتیوب", url=YOUTUBE_URL)],
        [InlineKeyboardButton("🎵 آرشیو آهنگ‌ها", callback_data="archive_0")],
        [InlineKeyboardButton("🔎 جستجوی آهنگ", callback_data="search_start"),
         InlineKeyboardButton("🔥 جدیدترین آهنگ‌ها", callback_data="latest_songs")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "✨ به Deep House Farsi خوش آمدید\n\n"
        "🎧 آرشیو اختصاصی آهنگ‌های ما\n"
        "برای دریافت آهنگ موردنظر، از گزینه‌های زیر استفاده کنید ❤️"
    )
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=get_main_menu_markup())

async def add_song_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("شما دسترسی مدیریتی ندارید.")
        return

    if not context.args:
        await update.message.reply_text(
            "⚠️ راهنمای افزودن آهنگ:\n"
            "/add نام آهنگ\n(سپس فایل صوتی را ارسال کنید)"
        )
        return
    
    song_title = "🎵 " + " ".join(context.args)
    context.user_data['pending_title'] = song_title
    await update.message.reply_text(f"✅ عنوان «{song_title}» ثبت شد.\nاکنون فایل صوتی یا موزیک‌ویدیو را بفرستید.")

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global SONGS
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        if context.user_data.get('waiting_for_search'):
            context.user_data['waiting_for_search'] = False
            query_text = update.message.text.strip()
            SONGS = load_songs()
            
            matched = []
            for s_id, info in SONGS.items():
                if query_text.lower() in info['title'].lower():
                    matched.append((s_id, info))
            
            keyboard = []
            for s_id, info in matched[:10]:
                keyboard.append([InlineKeyboardButton(f"🎧 {info['title']}", callback_data=f"sel_{s_id}")])
            keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")])
            
            if matched:
                await update.message.reply_text(
                    f"🔎 نتایج جستجو برای: {query_text}\nتعداد یافت‌شده: {len(matched)}",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await update.message.reply_text(
                    f"❌ هیچ آهنگی با عبارت «{query_text}» یافت نشد.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]])
                )
        return

    msg = update.message
    file_id = None
    
    if msg.audio:
        file_id = msg.audio.file_id
    elif msg.voice:
        file_id = msg.voice.file_id
    elif msg.document:
        file_id = msg.document.file_id

    if file_id:
        if 'pending_title' in context.user_data:
            title = context.user_data.pop('pending_title')
            SONGS = load_songs()
            song_id = uuid.uuid4().hex[:8]
            
            SONGS[song_id] = {
                "title": title,
                "file_id": file_id,
                "downloads": 0
            }
            save_songs(SONGS)
            
            await update.message.reply_text(
                f"🎉 آهنگ جدید با موفقیت ذخیره شد!\n\n🔹 عنوان: {title}\n🔹 شناسه: {song_id}"
            )
        else:
            await update.message.reply_text(
                f"📁 فایل‌آیدی دریافت شد:\n{file_id}\n\nبرای ثبت نهایی بنویسید:\n/add نام آهنگ"
            )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global SONGS
    SONGS = load_songs()
    
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "main_menu":
        context.user_data['waiting_for_search'] = False
        await query.message.edit_text(
            "✨ به Deep House Farsi خوش آمدید\n\n"
            "🎧 آرشیو اختصاصی آهنگ‌های ما\n"
            "برای دریافت آهنگ موردنظر، از گزینه‌های زیر استفاده کنید ❤️",
            reply_markup=get_main_menu_markup()
        )

    elif data.startswith("archive_"):
        page = int(data.split("_")[1])
        song_items = list(SONGS.items())
        total_songs = len(song_items)
        max_page = (total_songs - 1) // PAGE_SIZE if total_songs > 0 else 0
        
        start_idx = page * PAGE_SIZE
        end_idx = start_idx + PAGE_SIZE
        page_items = song_items[start_idx:end_idx]
        
        keyboard = []
        for s_id, info in page_items:
            keyboard.append([InlineKeyboardButton(f"🎧 {info['title']}", callback_data=f"sel_{s_id}")])
        
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ صفحه قبل", callback_data=f"archive_{page - 1}"))
        nav_buttons.append(InlineKeyboardButton(f"📄 {page + 1} / {max_page + 1}", callback_data="noop"))
        if end_idx < total_songs:
            nav_buttons.append(InlineKeyboardButton("صفحه بعد ➡️", callback_data=f"archive_{page + 1}"))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")])
        
        if total_songs == 0:
            text = "📂 آرشیو آهنگ‌ها در حال حاضر خالی است."
        else:
            text = f"📂 آرشیوی از بهترین‌های Deep House\nصفحه {page + 1} از {max_page + 1}:"

        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "search_start":
        context.user_data['waiting_for_search'] = True
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]])
        await query.message.edit_text(
            "🔎 جستجوی آهنگ\n\nلطفاً نام یا بخشی از نام آهنگ موردنظر خود را ارسال کنید:",
            reply_markup=keyboard
        )

    elif data == "latest_songs":
        song_items = list(SONGS.items())
        latest = song_items[-10:][::-1]
        
        keyboard = []
        for s_id, info in latest:
            keyboard.append([InlineKeyboardButton(f"🔥 {info['title']}", callback_data=f"sel_{s_id}")])
        keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")])
        
        if not latest:
            text = "🔥 هیچ آهنگ جدیدی یافت نشد."
        else:
            text = "🔥 جدیدترین آهنگ‌های اضافه شده:"

        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "noop":
        pass

    elif data.startswith("sel_"):
        song_id = data.replace("sel_", "")
        if song_id in SONGS:
            song_info = SONGS[song_id]
            keyboard = [
                [InlineKeyboardButton("❤️ عضویت در یوتیوب", url=YOUTUBE_URL)],
                [InlineKeyboardButton("✅ سابسکرایب کردم، دریافت فایل", callback_data=f"verify_{song_id}")],
                [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.edit_text(
                f"⚠️ مرحله تایید سابسکرایب\n\n"
                f"برای دریافت موزیک {song_info['title']}، لطفاً مطمئن شوید که کانال یوتیوب ما را سابسکرایب کرده‌اید و سپس روی دکمه تایید بزنید.",
                reply_markup=reply_markup
            )

    elif data.startswith("verify_"):
        song_id = data.replace("verify_", "")
        if song_id in SONGS:
            song_info = SONGS[song_id]
            await query.message.edit_text(f"🎉 سپاس از حمایت شما!\nدر حال ارسال فایل {song_info['title']}...")
            
            chat_id = query.message.chat_id
            file_id = song_info["file_id"]
            caption = f"🎵 {song_info['title']}\n\n🔗 کانال رسمی ما: @DeepHouse_Farsi"
            
            sent = False
            try:
                await context.bot.send_audio(chat_id=chat_id, audio=file_id, caption=caption)
                sent = True
            except Exception as e:
                logging.error(f"Failed to send audio: {e}")
                try:
                    await context.bot.send_document(chat_id=chat_id, document=file_id, caption=caption)
                    sent = True
                except Exception as e2:
                    logging.error(f"Failed to send document: {e2}")
            
            if sent:
                SONGS[song_id]["downloads"] += 1
                save_songs(SONGS)
                
                back_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]])
                await context.bot.send_message(chat_id=chat_id, text="👇 برای دریافت سایر آهنگ‌ها از منو استفاده کنید:", reply_markup=back_keyboard)
            else:
                await context.bot.send_message(chat_id=chat_id, text="❌ خطا در ارسال فایل. لطفاً به ادمین اطلاع دهید.")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global SONGS
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("شما دسترسی مدیریتی ندارید.")
        return

    SONGS = load_songs()
    total_songs = len(SONGS)
    stats_text = f"📊 گزارش آمار ربات\n\n🎵 مجموع آهنگ‌ها: {total_songs}\n\n"
    for song_id, info in SONGS.items():
        stats_text += f"• {info['title']}: 📥 {info['downloads']} دانلود\n"
    
    await update.message.reply_text(stats_text)

# راه‌اندازی اپلیکیشن تلگرام
telegram_app = Application.builder().token(TOKEN).build()
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("add", add_song_command))
telegram_app.add_handler(CommandHandler("stats", stats))
telegram_app.add_handler(MessageHandler(filters.AUDIO | filters.VOICE | filters.Document.ALL | filters.TEXT & ~filters.COMMAND, handle_media))
telegram_app.add_handler(CallbackQueryHandler(button))

@app.before_first_request
def setup_webhook():
    if RENDER_EXTERNAL_URL:
        webhook_url = f"{RENDER_EXTERNAL_URL.rstrip('/')}/webhook"
        telegram_app.bot.set_webhook(url=webhook_url)
        logging.info(f"Webhook set to: {webhook_url}")

@app.route("/", methods=["GET"])
def index():
    return "Bot is running!", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_string = request.get_data().decode("utf-8")
        update = Update.de_json(json_string, telegram_app.bot)
        
        # اجرای ناهمگام آپدیت‌ها در لوپ برنامه
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(telegram_app.process_update(update), loop)
        else:
            loop.run_until_complete(telegram_app.process_update(update))
            
        return "OK", 200
    return "Invalid request", 403

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
