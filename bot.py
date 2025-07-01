import os
import sys
import logging
import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pymongo import MongoClient

# ==== ENV VARS ====
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MONGO_URI = os.environ.get("MONGO_URI")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))
LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL"))

app = Client("downloader_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
mongo = MongoClient(MONGO_URI)
db = mongo[MONGO_DB_NAME]
users_col = db["users"]
cookies_path = "cookies.txt"
logging.basicConfig(level=logging.INFO)

# ==== TEXTS ====
START_MSG = """**👋 Welcome to Downloader Bot!**

Send me a link from **TikTok, YouTube, Instagram, Facebook** or other supported sites.

__I will download it for you (max 500MB)__.
"""

ABOUT_TEXT = """╔════❰  **About the Bot**  ❱═❍⊱❁۪۪
║╭━━━━━━━━━━━━━━━➣
║┣⪼ 📃 **Bot**: Media Downloader
║┣⪼ 👑 **Creator**: [@BOSS1480](https://t.me/BOSS1480)
║┣⪼ 📢 **Updates**: [Tj_Bots](https://t.me/Tj_Bots)
║┣⪼ 📡 **Hosted on**: [Heroku](https://heroku.com)
║┣⪼ 🧠 **Language**: [Python](https://python.org)
║┣⪼ 📚 **Library**: [Pyrogram](https://docs.pyrogram.org)
║┣⪼ 🗒️ **Version**: v2.5.4
║╰━━━━━━━━━━━━━━━➣
╚══════════════════❍⊱❁۪۪
"""

HELP_TEXT = """**ℹ️ How to use the bot**

1. Just send a link from TikTok, YouTube, Instagram, etc.
2. Bot will download and upload it to Telegram.
3. Max file size: 500MB.
"""

BUTTONS = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("📃 About", callback_data="about"),
        InlineKeyboardButton("❓ Help", callback_data="help")
    ],
    [InlineKeyboardButton("📢 Updates", url="https://t.me/Tj_Bots")]
])

BACK_BUTTON = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="start")]])

# ==== HANDLERS ====

@app.on_message(filters.command("start") & filters.private)
def start(client, message: Message):
    user_id = message.from_user.id
    if not users_col.find_one({"_id": user_id}):
        users_col.insert_one({"_id": user_id})
    try:
        app.send_message(LOG_CHANNEL, f"#NewUser\nID: `{user_id}`\nName: {message.from_user.mention}")
    except:
        pass
    message.reply(START_MSG, reply_markup=BUTTONS, parse_mode="markdown")

@app.on_callback_query()
def callback(client, cb):
    if cb.data == "about":
        cb.message.edit_text(ABOUT_TEXT, reply_markup=BACK_BUTTON, parse_mode="markdown", disable_web_page_preview=True)
    elif cb.data == "help":
        cb.message.edit_text(HELP_TEXT, reply_markup=BACK_BUTTON)
    elif cb.data == "start":
        cb.message.edit_text(START_MSG, reply_markup=BUTTONS)

@app.on_message(filters.command("cookies") & filters.reply & filters.user(ADMIN_ID))
def save_cookies(client, message: Message):
    if message.reply_to_message and message.reply_to_message.document:
        message.reply_to_message.download(file_name=cookies_path)
        message.reply("✅ `cookies.txt` saved.", parse_mode="markdown")

@app.on_message(filters.command("broadcast") & filters.user(ADMIN_ID))
def broadcast(client, message: Message):
    if not message.reply_to_message:
        return message.reply("Reply to a message to broadcast.")
    sent = failed = 0
    for user in users_col.find():
        try:
            app.copy_message(user["_id"], message.chat.id, message.reply_to_message.id)
            sent += 1
        except:
            failed += 1
    message.reply(f"✅ Broadcast sent to {sent} users. Failed: {failed}")

@app.on_message(filters.command("stats") & filters.user(ADMIN_ID))
def stats(client, message: Message):
    count = users_col.count_documents({})
    message.reply(f"👥 Total users: {count}")

@app.on_message(filters.command("restart") & filters.user(ADMIN_ID))
def restart(client, message: Message):
    message.reply("🔄 Restarting bot...")
    os.execl(sys.executable, sys.executable, *sys.argv)

@app.on_message(filters.private & filters.text & ~filters.command(["start", "cookies", "broadcast", "stats", "restart"]))
def handle_links(client, message: Message):
    url = message.text.strip()
    user_id = message.from_user.id
    try:
        app.send_message(LOG_CHANNEL, f"#NewLink\nUser: {message.from_user.mention}\nLink: {url}")
    except:
        pass

    status = message.reply("🔄 Downloading...")
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'noplaylist': True,
        'quiet': True,
        'cookiefile': cookies_path if os.path.exists(cookies_path) else None,
        'max_filesize': 500 * 1024 * 1024,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            caption = f"[{info.get('title', 'File')}]({url})"
            mime = info.get("ext", "")

            if mime in ["mp4", "mkv", "webm"]:
                app.send_video(message.chat.id, file_path, caption=caption, parse_mode="markdown")
            elif mime in ["jpg", "jpeg", "png", "webp"]:
                app.send_photo(message.chat.id, file_path, caption=caption, parse_mode="markdown")
            else:
                app.send_document(message.chat.id, file_path, caption=caption, parse_mode="markdown")

            app.send_message(LOG_CHANNEL, f"✅ Uploaded", reply_to_message_id=status.id)
    except Exception as e:
        message.reply(f"❌ Error: `{str(e)}`", parse_mode="markdown")
        try:
            app.send_message(LOG_CHANNEL, f"❌ Error:\n{str(e)}", disable_web_page_preview=True)
        except:
            pass
    finally:
        status.delete()

app.run()
