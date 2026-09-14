import os
import logging
import json
import asyncio
import threading
import uuid
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("خطا: متغیر محیطی BOT_TOKEN تنظیم نشده است.")

admin_id_env = os.environ.get("ADMIN_ID")
if not admin_id_env:
    raise ValueError("خطا: متغیر محیطی ADMIN_ID تنظیم نشده است.")
ADMIN_ID = int(admin_id_env)

YOUTUBE_URL = "https://www.youtube.com/@DeepHouse_Farsi?sub_confirmation=1"
DB_FILE = "songs_db.json"
PAGE_SIZE = 10

def load_songs():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return {}
                return json.loads(content)
        except Exception as e:
            logging.error(f"Error reading {DB_FILE}: {e}. Returning empty database.")
    return {}

def save_songs(songs):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(songs, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Error saving to {DB_FILE}: {e}")

SONGS = load_songs()

app = Flask(__name__)

application = Application.builder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "✨ **به Deep House Farsi خوش آمدید**\n\n"
        "🎧 آرشیو اختصاصی آهنگ‌های ما\n"
        "برای دریافت آهنگ موردنظر، از گزینه‌های زیر استفاده کنید ❤️"
    )
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=get_main_menu_markup(), parse_mode="Markdown")

async def add_song_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("شما دسترسی مدیریتی ندارید.")
        return

    if not context.args:
        await update.message.reply_text(
            "⚠️ **راهنمای افزودن آهنگ:**\n"
            "`/add نام آهنگ`\n(سپس فایل صوتی را ارسال کنید)",
            parse_mode="Markdown"
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
                    f"🔎 **نتایج جستجو برای:** `{query_text}`\nتعداد یافت‌شده: {len(matched)}",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text(
                    f"❌ هیچ آهنگی با عبارت «{query_text}» یافت نشد.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]]),
                    parse_mode="Markdown"
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
                f"🎉 **آهنگ جدید با موفقیت ذخیره شد!**\n\n🔹 عنوان: {title}\n🔹 شناسه: `{song_id}`",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                f"📁 **فایل‌آیدی دریافت شد:**\n`{file_id}`\n\nبرای ثبت نهایی بنویسید:\n`/add نام آهنگ`",
                parse_mode="Markdown"
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
            "✨ **به Deep House Farsi خوش آمدید**\n\n"
            "🎧 آرشیو اختصاصی آهنگ‌های ما\n"
            "برای دریافت آهنگ موردنظر، از گزینه‌های زیر استفاده کنید ❤️",
            reply_markup=get_main_menu_markup(),
            parse_mode="Markdown"
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
            text = f"📂 **آرشیوی از بهترین‌های Deep House**\nصفحه {page + 1} از {max_page + 1}:"

        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "search_start":
        context.user_data['waiting_for_search'] = True
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")]])
        await query.message.edit_text(
            "🔎 **جستجوی آهنگ**\n\nلطفاً نام یا بخشی از نام آهنگ موردنظر خود را ارسال کنید:",
            reply_markup=keyboard,
            parse_mode="Markdown"
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
            text = "🔥 **جدیدترین آهنگ‌های اضافه شده:**"

        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

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
                f"⚠️ **مرحله تایید سابسکرایب**\n\n"
                f"برای دریافت موزیک **{song_info['title']}**، لطفاً مطمئن شوید که کانال یوتیوب ما را سابسکرایب کرده‌اید و سپس روی دکمه تایید بزنید.",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )

    elif data.startswith("verify_"):
        song_id = data.replace("verify_", "")
        if song_id in SONGS:
            song_info = SONGS[song_id]
            await query.message.edit_text(f"🎉 سپاس از حمایت شما!\nدر حال ارسال فایل **{song_info['title']}**...")
            
            chat_id = query.message.chat_id
            file_id = song_info["file_id"]
            caption = f"🎵 {song_info['title']}\n\n🔗 کانال رسمی ما: @DeepHouse_Farsi"
            
            sent = False
            try:
                await context.bot.send_audio(chat_id=chat_id, audio=file_id, caption=caption, parse_mode="Markdown")
                sent = True
            except Exception as e:
                logging.error(f"Failed to send audio: {e}")
                try:
                    await context.bot.send_document(chat_id=chat_id, document=file_id, caption=caption, parse_mode="Markdown")
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
    stats_text = f"📊 **گزارش آمار ربات**\n\n🎵 مجموع آهنگ‌ها: {total_songs}\n\n"
    for song_id, info in SONGS.items():
        stats_text += f"• {info['title']}: 📥 `{info['downloads']}` دانلود\n"
    
    await update.message.reply_text(stats_text, parse_mode="Markdown")

def get_main_menu_markup():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❤️ عضویت در یوتیوب", url=YOUTUBE_URL)],
        [InlineKeyboardButton("🎵 آرشیو آهنگ‌ها", callback_data="archive_0")],
        [InlineKeyboardButton("🔎 جستجوی آهنگ", callback_data="search_start"),
         InlineKeyboardButton("🔥 جدیدترین آهنگ‌ها", callback_data="latest_songs")]
    ])

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("add", add_song_command))
application.add_handler(CommandHandler("stats", stats))
application.add_handler(MessageHandler(filters.AUDIO | filters.VOICE | filters.Document.ALL | filters.TEXT & ~filters.COMMAND, handle_media))
application.add_handler(CallbackQueryHandler(button))

bot_loop = None
bot_thread = None
is_initialized = False

def run_async_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

def init_bot_background():
    global bot_loop, bot_thread, is_initialized
    if is_initialized:
        return
    
    bot_loop = asyncio.new_event_loop()
    bot_thread = threading.Thread(target=run_async_loop, args=(bot_loop,), daemon=True)
    bot_thread.start()
    
    async def _setup():
        await application.initialize()
        await application.start()
        
        render_external_url = os.environ.get("RENDER_EXTERNAL_URL")
        if render_external_url:
            webhook_url = f"{render_external_url}/{TOKEN}"
            await application.bot.set_webhook(webhook_url)
            logging.info(f"Webhook set to: {webhook_url}")

    future = asyncio.run_coroutine_threadsafe(_setup(), bot_loop)
    future.result()
    is_initialized = True

init_bot_background()

@app.route("/")
def index():
    return "Bot is running perfectly!", 200

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    if request.method == "POST":
        json_data = request.get_json(force=True)
        update = Update.de_json(json_data, application.bot)
        if update and bot_loop:
            bot_loop.call_soon_threadsafe(application.update_queue.put_nowait, update)
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
