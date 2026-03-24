import os
import logging
import asyncio
from aiohttp import web
import requests
from telegram import Update, WebAppInfo, MenuButtonWebApp
from telegram.ext import Application, MessageHandler, filters, ContextTypes, ApplicationBuilder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_KEY")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
ALLOWED_USERS = [OWNER_ID] if OWNER_ID else []

WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

async def get_available_model():
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"
    try:
        response = requests.get(url, timeout=10)
        models = response.json().get('models', [])
        for m in models:
            if "generateContent" in m.get('supportedGenerationMethods', []):
                return m['name']
        return "models/gemini-2.5-flash"
    except Exception as e:
        logger.error(f"Model fetch error: {e}")
        return "models/gemini-2.5-flash"

ACTIVE_MODEL = asyncio.get_event_loop().run_until_complete(get_available_model())

def get_gemini_response(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/{ACTIVE_MODEL}:generateContent?key={GEMINI_KEY}"
    headers = {'Content-Type': 'application/json'}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        data = response.json()
        if 'candidates' in data:
            return data['candidates'][0]['content']['parts'][0]['text']
        logger.error(f"Unexpected response: {data}")
        return f"⚠️ رد غير متوقع"
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return f"❌ خطأ تقني"

async def send_long_message(update, text):
    if not text:
        return
    for i in range(0, len(text), 4000):
        await update.message.reply_text(text[i:i+4000])

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USERS:
        logger.warning(f"Unauthorized access from {update.effective_user.id}")
        return

    text = update.message.text
    if text:
        response_text = get_gemini_response(text)
        await send_long_message(update, response_text)

async def webhook_handler(request):
    if WEBHOOK_SECRET and request.headers.get('X-Telegram-Bot-Api-Secret-Token') != WEBHOOK_SECRET:
        logger.warning("Invalid webhook secret")
        return web.Response(status=403)
    
    try:
        data = await request.json()
        update = Update.de_json(data, context.bot)
        await handle_message(update, request.app['context'])
    except Exception as e:
        logger.error(f"Webhook error: {e}")
    
    return web.Response(status=200)

async def on_startup(app):
    await app.bot.set_webhook(
        url=f"{WEBHOOK_HOST}{WEBHOOK_PATH}",
        secret_token=WEBHOOK_SECRET,
        drop_pending_updates=True
    )
    logger.info(f"Webhook set to {WEBHOOK_HOST}{WEBHOOK_PATH}")

async def on_shutdown(app):
    await app.bot.delete_webhook()
    logger.info("Webhook deleted")

def run_webhook():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    context = ContextTypes.DEFAULT_TYPE.from_application(app)
    
    application = web.Application(middlewares=[security_middleware])
    application['context'] = context
    application.router.add_post(WEBHOOK_PATH, webhook_handler)
    application.on_startup.append(on_startup)
    application.on_shutdown.append(on_shutdown)
    
    return application

async def security_middleware(app, handler):
    async def middleware(request):
        if request.remote_addr in os.getenv("BLOCKED_IPS", "").split(","):
            return web.Response(status=403)
        return await handler(request)
    return middleware

def main():
    if not all([TELEGRAM_TOKEN, GEMINI_KEY, OWNER_ID, WEBHOOK_HOST]):
        logger.error("Missing required environment variables!")
        logger.info("Required: TELEGRAM_TOKEN, GEMINI_KEY, OWNER_ID, WEBHOOK_HOST")
        return

    app = run_webhook()
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))

if __name__ == "__main__":
    main()
