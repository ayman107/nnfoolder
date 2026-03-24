import os
import logging
import io
import base64
import asyncio
import nest_asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler

nest_asyncio.apply()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_KEY")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
ALLOWED_USERS = [OWNER_ID] if OWNER_ID else []

async def get_available_model():
    import requests
    url = f"https://generativelanguage.googleapis.com/v1/models?key={GEMINI_KEY}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        models = data.get('models', [])
        vision_models = ["gemini-1.5-pro", "gemini-2.0-flash", "gemini-2.5-flash"]
        for m in models:
            name = m.get('name', '').replace('models/', '')
            if name in vision_models and "generateContent" in m.get('supportedGenerationMethods', []):
                return f"models/{name}"
        for m in models:
            if "generateContent" in m.get('supportedGenerationMethods', []):
                return m['name']
        return "models/gemini-2.5-flash"
    except Exception as e:
        logger.error(f"Model fetch error: {e}")
        return "models/gemini-2.5-flash"

ACTIVE_MODEL = None

def get_gemini_response(prompt, image_data=None):
    import requests
    url = f"https://generativelanguage.googleapis.com/v1beta/{ACTIVE_MODEL}:generateContent?key={GEMINI_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    if image_data:
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt} if prompt else {"text": "Describe this image"},
                    {"inline_data": {"mime_type": "image/jpeg", "data": image_data}}
                ]
            }]
        }
    else:
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        data = response.json()
        if 'candidates' in data:
            return data['candidates'][0]['content']['parts'][0]['text']
        logger.error(f"Unexpected response: {data}")
        return f"⚠️ رد غير متوقع"
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return f"❌ خطأ تقني: {str(e)}"

async def send_long_message(update, text):
    if not text:
        return
    for i in range(0, len(text), 4000):
        await update.message.reply_text(text[i:i+4000])

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        logger.warning(f"Unauthorized access from {update.effective_user.id}")
        await update.message.reply_text("⛔ غير مصرح")
        return

    text = update.message.text
    await update.message.reply_text("🤖 جاري المعالجة...")
    response = get_gemini_response(text)
    await send_long_message(update, response)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        logger.warning(f"Unauthorized access from {update.effective_user.id}")
        await update.message.reply_text("⛔ غير مصرح")
        return

    await update.message.reply_text("🤖 جاري تحليل الصورة...")
    
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        
        downloaded = await file.download_as_bytearray()
        image_data = base64.b64encode(downloaded).decode('utf-8')
        
        caption = update.message.caption or ""
        
        response = get_gemini_response(caption, image_data)
        await send_long_message(update, response)
    except Exception as e:
        logger.error(f"Photo error: {e}")
        await update.message.reply_text(f"❌ خطأ: {str(e)}")

async def handle_document_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        return

    doc = update.message.document
    if doc.mime_type and doc.mime_type.startswith('image/'):
        await update.message.reply_text("🤖 جاري تحليل الصورة...")
        try:
            file = await context.bot.get_file(doc.file_id)
            downloaded = await file.download_as_bytearray()
            image_data = base64.b64encode(downloaded).decode('utf-8')
            caption = update.message.caption or ""
            response = get_gemini_response(caption, image_data)
            await send_long_message(update, response)
        except Exception as e:
            logger.error(f"Document image error: {e}")
            await update.message.reply_text(f"❌ خطأ: {str(e)}")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text("⛔ غير مصرح")
        return
    await update.message.reply_text(
        "🤖 *MeClaw Bot*\n\n"
        "• أرسل رسالة نصية للدردشة مع AI\n"
        "• أرسل صورة لتحليلها\n"
        "• أضف تعليق على الصورة",
        parse_mode="Markdown"
    )

async def post_init(application: Application):
    global ACTIVE_MODEL
    ACTIVE_MODEL = await get_available_model()
    logger.info(f"🚀 Bot started with model: {ACTIVE_MODEL}")

def main():
    if not all([TELEGRAM_TOKEN, GEMINI_KEY, OWNER_ID]):
        logger.error("Missing required environment variables!")
        logger.info("Required: TELEGRAM_TOKEN, GEMINI_KEY, OWNER_ID")
        return

    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .post_init(post_init)
        .build()
    )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.Document.IMAGE, handle_document_image))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Starting polling...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
