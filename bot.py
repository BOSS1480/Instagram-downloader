import os
import sys
import logging
import yt_dlp
import mimetypes
import subprocess
import psutil
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
GITHUB_REPO = os.environ.get("GITHUB_REPO", "https://github.com/BOSS1480/Instagram-downloader")

app = Client("downloader_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
mongo = MongoClient(MONGO_URI)
db = mongo[MONGO_DB_NAME]
users_col = db["users"]
cookies_path = "cookies.txt"
logging.basicConfig(level=logging.INFO)

# ==== TEXTS ====
START_MSG = """Welcome to Downloader Bot!

Send me a link from TikTok, YouTube, Instagram, Facebook or other supported sites.

I will download it for you (max 500MB).
"""

ABOUT_TEXT = """About the Bot
Bot: Media Downloader
Creator: @BOSS1480
Updates: Tj_Bots
Hosted on: Heroku
Language: Python
Library: Pyrogram
Version: v2.5.4
"""

HELP_TEXT = """How to use the bot

1. Just send a link from TikTok, YouTube, Instagram, etc.
2. Bot will download and upload it to Telegram.
3. Max file size: 500MB.
"""

BUTTONS = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("Help", callback_data="help"),
        InlineKeyboardButton("About", callback_data="about")
    ],
    [InlineKeyboardButton("Updates", url="https://t.me/Tj_Bots")]
])

BACK_BUTTON = InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data="start")]])

# ==== STATUS FUNCTION ====
def get_server_status():
    # CPU
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_cores = psutil.cpu_count(logical=True)
    
    # RAM
    memory = psutil.virtual_memory()
    ram_total = memory.total / (1024 ** 3)  # Convert to GB
    ram_used = memory.used / (1024 ** 3)
    ram_percent = memory.percent
    
    # Storage
    disk = psutil.disk_usage('/')
    disk_total = disk.total / (1024 ** 3)
    disk_used = disk.used / (1024 ** 3)
    disk_percent = disk.percent
    
    # Progress bars
    def progress_bar(percent):
        filled = int(percent // 10)
        return "█" * filled + "▒" * (10 - filled)
    
    status_text = (
        f"Server Status\n\n"
        f"CPU Usage: {cpu_percent}% ({cpu_cores} cores)\n"
        f"{progress_bar(cpu_percent)} {cpu_percent}%\n\n"
        f"RAM: {ram_used:.2f}/{ram_total:.2f} GB\n"
        f"{progress_bar(ram_percent)} {ram_percent}%\n\n"
        f"Storage: {disk_used:.2f}/{disk_total:.2f} GB\n"
        f"{progress_bar(disk_percent)} {disk_percent}%"
    )
    
    return status_text, InlineKeyboardMarkup([[InlineKeyboardButton("Update", callback_data="update_status")]])

# ==== HANDLERS ====

@app.on_message(filters.command("start") & filters.private)
def start(client, message: Message):
    user_id = message.from_user.id
    if not users_col.find_one({"_id": user_id}):
        users_col.insert_one({"_id": user_id})
    try:
        app.send_message(LOG_CHANNEL, f"#NewUser\nID: {user_id}\nName: {message.from_user.first_name}")
    except:
        pass
    message.reply(START_MSG, reply_markup=BUTTONS)

@app.on_message(filters.command("status") & filters.user(ADMIN_ID))
def status(client, message: Message):
    status_text, status_buttons = get_server_status()
    message.reply(status_text, reply_markup=status_buttons)

@app.on_callback_query()
def callback(client, cb):
    if cb.data == "about":
        cb.message.edit_text(ABOUT_TEXT, reply_markup=BACK_BUTTON)
    elif cb.data == "help":
        cb.message.edit_text(HELP_TEXT, reply_markup=BACK_BUTTON)
    elif cb.data == "start":
        cb.message.edit_text(START_MSG, reply_markup=BUTTONS)
    elif cb.data == "update_status":
        status_text, status_buttons = get_server_status()
        cb.message.edit_text(status_text, reply_markup=status_buttons)

@app.on_message(filters.command("cookies") & filters.reply & filters.user(ADMIN_ID))
def save_cookies(client, message: Message):
    if message.reply_to_message and message.reply_to_message.document:
        message.reply_to_message.download(file_name=cookies_path)
        message.reply("cookies.txt saved.")
    else:
        message.reply("Please reply to a document containing cookies.")

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
    message.reply(f"Broadcast sent to {sent} users. Failed: {failed}")

@app.on_message(filters.command("stats") & filters.user(ADMIN_ID))
def stats(client, message: Message):
    count = users_col.count_documents({})
    message.reply(f"Total users: {count}")

@app.on_message(filters.command("restart") & filters.user(ADMIN_ID))
def restart(client, message: Message):
    message.reply("Restarting bot...")
    try:
        if GITHUB_REPO:
            subprocess.run(["git", "pull", GITHUB_REPO], check=True)
            message.reply("Code updated from GitHub.")
    except Exception as e:
        message.reply(f"Error pulling GitHub: {e}")
    os.execl(sys.executable, sys.executable, *sys.argv)

@app.on_message(filters.private & filters.text & ~filters.command(["start", "cookies", "broadcast", "stats", "restart", "status"]))
def handle_links(client, message: Message):
    url = message.text.strip()
    user_id = message.from_user.id
    try:
        app.send_message(LOG_CHANNEL, f"#NewLink\nUser: {message.from_user.first_name}\nLink: {url}")
    except:
        pass

    status = message.reply("Downloading...")
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
            caption = f"{info.get('title', 'File')} - {url}"
            ext = info.get("ext", "")
            mime = mimetypes.guess_type(file_path)[0]

            if mime and mime.startswith("video"):
                app.send_video(message.chat.id, file_path, caption=caption)
            elif mime and mime.startswith("image"):
                app.send_photo(message.chat.id, file_path, caption=caption)
            else:
                app.send_document(message.chat.id, file_path, caption=caption)

            app.send_message(LOG_CHANNEL, "Uploaded", reply_to_message_id=status.id)
    except Exception as e:
        message.reply(f"Error: {str(e)}")
        try:
            app.send_message(LOG_CHANNEL, f"Error: {str(e)}")
        except:
            pass
    finally:
        status.delete()

app.run()
