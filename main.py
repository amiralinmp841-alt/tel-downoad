import os
from flask import Flask, request
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from yt_dlp import YoutubeDL

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # در Render تنظیم میکنی

app = Flask(__name__)
application = Application.builder().token(TOKEN).build()


# استخراج اطلاعات ویدیو
def extract_video_info(url):
    ydl_opts = {"quiet": True, "dump_single_json": True}
    with YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)


# دانلود فایل با کیفیت انتخابی
def download_video(url, format_id):
    ydl_opts = {
        "format": format_id,
        "outtmpl": "/tmp/video.%(ext)s",
    }
    with YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(result)


# شروع
async def start(update: Update, context):
    await update.message.reply_text("سلام! لینک هر صفحه‌ای رو بفرست تا ویدیوهاشو برات بفرستم.")


# وقتی لینک می‌فرسته
async def handle_link(update: Update, context):
    url = update.message.text.strip()

    await update.message.reply_text("⏳ در حال بررسی لینک...")

    try:
        info = extract_video_info(url)

        # اگر چند ویدیو داخل صفحه بود (مثل playlist)
        entries = info.get("entries", [info])

        for video in entries:
            formats = video.get("formats", [])
            video_id = video.get("id")

            # استخراج کیفیت‌ها
            quality_options = []
            for f in formats:
                if f.get("vcodec") != "none":
                    q = f.get("format_id")
                    label = f"{f.get('height', '???')}p  -  {f.get('ext')}"
                    quality_options.append((label, q))

            # اگر فقط یک کیفیت هست → مستقیم ارسال کنیم
            if len(quality_options) == 1:
                filepath = download_video(video["webpage_url"], quality_options[0][1])
                await update.message.reply_video(open(filepath, "rb"))
                continue

            # اگر چند کیفیت هست → دکمه‌ها را بفرست
            keyboard = [
                [
                    InlineKeyboardButton(label, callback_data=f"{video['webpage_url']}|{fmt}")
                ]
                for label, fmt in quality_options
            ]

            await update.message.reply_text(
                f"🎥 ویدیو: {video.get('title', 'Video')}\n"
                "یکی از کیفیت‌ها را انتخاب کن:",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

    except Exception as e:
        await update.message.reply_text(f"❌ خطا در پردازش لینک:\n{e}")


# وقتی کیفیت انتخاب می‌شود
async def quality_selected(update: Update, context):
    query = update.callback_query
    await query.answer()

    url, format_id = query.data.split("|")

    await query.edit_message_text("⏳ در حال دانلود ویدیو...")

    try:
        filepath = download_video(url, format_id)
        await query.message.reply_video(open(filepath, "rb"))

    except Exception as e:
        await query.message.reply_text(f"❌ خطا هنگام دانلود:\n{e}")


# اتصال هندلرها
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
application.add_handler(CallbackQueryHandler(quality_selected))


@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_update = request.get_json(force=True)
    update = Update.de_json(json_update, application.bot)

    import asyncio
    asyncio.create_task(application.process_update(update))

    return "ok"



@app.route("/")
def root():
    return "Bot is running!"


if __name__ == "__main__":
    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", 10000)),
        url_path=TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{TOKEN}",
    )
