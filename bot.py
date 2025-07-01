import os
import sys
import logging
import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pymongo import MongoClient

API_ID = int(os.environ.get("API_ID")) API_HASH = os.environ.get("API_HASH") BOT_TOKEN = os.environ.get("BOT_TOKEN") MONGO_URI = os.environ.get("MONGO_URI") MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME") ADMIN_ID = int(os.environ.get("ADMIN_ID")) LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL"))

app = Client("downloader", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN) mongo = MongoClient(MONGO_URI) db = mongo[MONGO_DB_NAME] users_col = db["users"] cookies_path = "cookies.txt"

logging.basicConfig(level=logging.INFO)

START_MSG = """ Welcome to the Downloader Bot!

Just send me a link from TikTok, Instagram, YouTube, Facebook and more, and I will download it for you (up to 500MB). """

BUTTONS = InlineKeyboardMarkup([ [ InlineKeyboardButton("📃 About", callback_data="about"), InlineKeyboardButton("❓ Help", callback_data="help") ], [InlineKeyboardButton("📢 Updates", url="https://t.me/Tj_Bots")] ])

ABOUT_TEXT = """ ╔════❰  𝗔𝗯𝗼𝘂𝘁 𝗧𝗵𝗲 𝗕𝗼𝘁  ❱═❍⊱❁۪۪ ║╭━━━━━━━━━━━━━━━➣ ║┣⪼📃 Bot : Downloader ║┣⪼👦 Creator : @BOSS1480 ║┣⪼🤖 Update : @Tj_Bots ║┣⪼📡 Hosted on : Heroku ║┣⪼🗣️ Language : Python ║┣⪼📚 Library : Pyrogram ║┣⪼🗒️ Version : v2.5.4 ║╰━━━━━━━━━━━━━━━➣ ╚══════════════════❍⊱❁۪۪ """

HELP_TEXT = """ How to use the bot:

Just send a video or image link from supported platforms (TikTok, YouTube, etc.)

Max file size: 500MB """


@app.on_message(filters.command("start") & filters.private) def start(client, message): user_id = message.from_user.id if not users_col.find_one({"_id": user_id}): users_col.insert_one({"_id": user_id}) try: app.send_message(LOG_CHANNEL, f"#NewUser\nID: {user_id}\nName: {message.from_user.mention}") except: pass message.reply(START_MSG, reply_markup=BUTTONS)

@app.on_callback_query() def cb_handler(client, cb): if cb.data == "about": cb.message.edit_text(ABOUT_TEXT, reply_markup=InlineKeyboardMarkup([ [InlineKeyboardButton("🔙 Back", callback_data="start")] ])) elif cb.data == "help": cb.message.edit_text(HELP_TEXT, reply_markup=InlineKeyboardMarkup([ [InlineKeyboardButton("🔙 Back", callback_data="start")] ])) elif cb.data == "start": cb.message.edit_text(START_MSG, reply_markup=BUTTONS)

@app.on_message(filters.command("cookies") & filters.reply & filters.user(ADMIN_ID)) def save_cookies(client, message): if message.reply_to_message.document: file = message.reply_to_message.download(file_name=cookies_path) message.reply("✅ cookies.txt saved.")

@app.on_message(filters.command("restart") & filters.user(ADMIN_ID)) def restart(client, message): message.reply("♻️ Restarting bot...") os.execv(sys.executable, ['python'] + sys.argv)

@app.on_message(filters.private & filters.text & ~filters.command(["start", "cookies", "restart"])) def handle_link(client, message: Message): user_id = message.from_user.id url = message.text.strip() try: app.send_message(LOG_CHANNEL, f"#NewLink\nUser: {message.from_user.mention}\nLink: {url}") except: pass processing = message.reply("🔄 Downloading...")

ydl_opts = {
    'format': 'bestvideo+bestaudio/best',
    'outtmpl': 'downloads/%(title)s.%(ext)s',
    'noplaylist': True,
    'quiet': True,
    'cookiefile': cookies_path if os.path.exists(cookies_path) else None,
    'max_filesize': 500*1024*1024,
}

try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info)
        caption = f"[{info.get('title', 'Downloaded File')}]({url})"
        mime = info.get("ext", "")

        if mime in ["mp4", "webm"]:
            app.send_video(
                message.chat.id,
                file_path,
                caption=caption,
                parse_mode="markdown",
                reply_to_message_id=message.id
            )
        elif mime in ["jpg", "jpeg", "png", "webp"]:
            app.send_photo(
                message.chat.id,
                file_path,
                caption=caption,
                parse_mode="markdown",
                reply_to_message_id=message.id
            )
        else:
            app.send_document(
                message.chat.id,
                file_path,
                caption=caption,
                parse_mode="markdown",
                reply_to_message_id=message.id
            )
        app.send_message(LOG_CHANNEL, f"✅ Uploaded", reply_to_message_id=processing.id)
except Exception as e:
    message.reply(f"❌ Error:\n`{str(e)}`")
    try: app.send_message(LOG_CHANNEL, f"❌ Error: {str(e)}\nFrom: {message.from_user.mention}")
    except: pass
finally:
    processing.delete()

@app.on_message(filters.command("broadcast") & filters.user(ADMIN_ID)) def broadcast(client, message): if not message.reply_to_message: return message.reply("Reply to a message to broadcast.") sent, failed = 0, 0 for user in users_col.find(): try: app.copy_message(user['_id'], message.chat.id, message.reply_to_message.id) sent += 1 except: failed += 1 message.reply(f"✅ Broadcast sent to {sent} users. Failed: {failed}")

@app.on_message(filters.command("stats") & filters.user(ADMIN_ID)) def stats(client, message): count = users_col.count_documents({}) message.reply(f"👥 Total users: {count}")

app.run()

