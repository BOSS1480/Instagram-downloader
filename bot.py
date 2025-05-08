import logging
import os
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import yt_dlp
import requests
import aiohttp
import aiohttp.web
import re
from urllib.parse import urlparse

# הגדרת לוגים
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# טוקן הבוט (הכנס את הטוקן שלך)
TOKEN = "7534270934:AAHCeBZADM58sLJri_v_TJMZwkDxUOhs5bs"

# פונקציה להורדת קובץ מטלגרם
async def download_telegram_file(file_url: str, file_path: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("מעבד קישור טלגרם...")
    try:
        response = requests.get(file_url, stream=True)
        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0
        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        await update.message.reply_text(f"מוריד... {percent:.2f}%")
        await update.message.reply_text("הורדה הושלמה! מעלה קובץ...")
        with open(file_path, "rb") as f:
            await context.bot.send_document(
                chat_id=update.effective_chat.id, document=f, caption="הקובץ שהורד מטלגרם"
            )
        await update.message.reply_text("העלאה הושלמה!")
        os.remove(file_path)  # מחיקת הקובץ לאחר ההעלאה
    except Exception as e:
        await update.message.reply_text(f"שגיאה בהורדת קובץ מטלגרם: {str(e)}")

# פונקציה להורדת וידאו מטיקטוק
async def download_tiktok_video(url: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("מעבד קישור טיקטוק...")
    try:
        ydl_opts = {
            "outtmpl": "tiktok_video.%(ext)s",
            "progress_hooks": [
                lambda d: progress_hook(d, update)
            ],
            "format": "best",
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        await update.message.reply_text("הורדה הושלמה! מעלה וידאו...")
        with open("tiktok_video.mp4", "rb") as f:
            await context.bot.send_video(
                chat_id=update.effective_chat.id, video=f, caption="הוידאו שהורד מטיקטוק"
            )
        await update.message.reply_text("העלאה הושלמה!")
        os.remove("tiktok_video.mp4")  # מחיקת הקובץ לאחר ההעלאה
    except Exception as e:
        await update.message.reply_text(f"שגיאה בהורדת וידאו מטיקטוק: {str(e)}")

# פונקציית התקדמות להורדה מטיקטוק
async def progress_hook(d, update: Update):
    if d["status"] == "downloading":
        percent = d.get("downloaded_bytes", 0) / d.get("total_bytes", 1) * 100
        await update.message.reply_text(f"מוריד... {percent:.2f}%")
    elif d["status"] == "finished":
        await update.message.reply_text("הורדה הושלמה!")

# פקודת /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "שלום! אני בוט שמוריד תמונות ווידאו מטלגרם וטיקטוק.\n"
        "שלח לי קישור לתוכן מטלגרם או טיקטוק, ואני אוריד אותו עבורך.\n"
        "אדווח על התקדמות: עיבוד, הורדה (עם אחוזים), והעלאה.\n"
        "התחל על ידי שליחת קישור!"
    )

# טיפול בהודעות עם קישורים
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text
    telegram_regex = r"https?://t\.me/.*"
    tiktok_regex = r"https?://(www\.)?(vm\.)?tiktok\.com/.*"

    if re.match(telegram_regex, message_text):
        file_name = os.path.basename(urlparse(message_text).path) or "telegram_file"
        file_path = f"downloads/{file_name}"
        os.makedirs("downloads", exist_ok=True)
        await download_telegram_file(message_text, file_path, update, context)
    elif re.match(tiktok_regex, message_text):
        await download_tiktok_video(message_text, update, context)
    else:
        await update.message.reply_text("אנא שלח קישור תקין מטלגרם או טיקטוק.")

# שרת Webhook עבור Koyeb
async def webhook(request):
    update = Update.de_json(await request.json(), app.bot)
    await app.process_update(update)
    return aiohttp.web.Response(text="OK")

# הגדרת האפליקציה וה-Webhook
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# הרצת השרת עבור Koyeb
if __name__ == "__main__":
    import asyncio

    async def main():
        # הגדרת Webhook
        webhook_url = "https://your-app.koyeb.app/webhook"  # החלף ב-URL של Koyeb
        await app.bot.set_webhook(webhook_url)

        # הרצת שרת aiohttp
        web_app = aiohttp.web.Application()
        web_app.router.add_post("/webhook", webhook)
        runner = aiohttp.web.AppRunner(web_app)
        await runner.setup()
        site = aiohttp.web.TCPSite(runner, "0.0.0.0", 8000)
        await site.start()
        print("Server running on 0.0.0.0:8000")

        # שמירה על הרצת הבוט
        await app.run_polling()

    asyncio.run(main())
