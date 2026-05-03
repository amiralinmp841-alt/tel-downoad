import os
import subprocess
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# ================== CONFIG ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # https://your-service.onrender.com
DOWNLOAD_DIR = "downloads"
MAX_SIZE_MB = 17
# ============================================

bot = Bot(BOT_TOKEN)
app_flask = Flask(__name__)
application = Application.builder().token(BOT_TOKEN).build()

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# -------- Video Download --------
def download_video(url):
    output = f"{DOWNLOAD_DIR}/%(title)s.%(ext)s"
    cmd = [
        "yt-dlp",
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "-o", output,
        url
    ]
    subprocess.run(cmd, check=True)

    files = sorted(
        [os.path.join(DOWNLOAD_DIR, f) for f in os.listdir(DOWNLOAD_DIR)],
        key=os.path.getctime
    )
    return files[-1]

# -------- Split Video --------
def split_video(video_path):
    parts_dir = video_path.replace(".mp4", "_parts")
    os.makedirs(parts_dir, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-c", "copy",
        "-map", "0",
        "-f", "segment",
        "-segment_size", str(MAX_SIZE_MB * 1024 * 1024),
        f"{parts_dir}/part_%03d.mp4"
    ]
    subprocess.run(cmd, check=True)

    return sorted(os.path.join(parts_dir, f) for f in os.listdir(parts_dir))

# -------- Handlers --------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎬 لینک ویدیو رو بفرست")

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    url = update.message.text

    await context.bot.send_message(chat_id, "⏳ در حال دانلود...")

    try:
        video = download_video(url)
        parts = split_video(video)

        for part in parts:
            await context.bot.send_video(
                chat_id=chat_id,
                video=open(part, "rb"),
                supports_streaming=True
            )

        await context.bot.send_message(chat_id, "✅ ارسال کامل شد")

    except Exception as e:
        await context.bot.send_message(chat_id, f"❌ خطا:\n{e}")

# -------- Telegram App --------
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))

# -------- Webhook Endpoint --------
@app_flask.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    application.update_queue.put_nowait(update)
    return "OK"

# -------- Render Entry --------
@app_flask.route("/")
def home():
    return "Bot is running"

if __name__ == "__main__":
    import asyncio

    async def main():
        await application.initialize()
        await bot.set_webhook(f"{WEBHOOK_URL}/webhook")

    asyncio.run(main())
    app_flask.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
