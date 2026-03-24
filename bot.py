import os
import logging
import asyncio
import json
import base64
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    filters, ContextTypes, CallbackQueryHandler
)
from telegram.constants import ParseMode

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Config:
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    GEMINI_KEY = os.getenv("GEMINI_KEY")
    OWNER_ID = int(os.getenv("OWNER_ID", "0"))
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///meclaw.db")
    ADMIN_IDS = [OWNER_ID]
    SECRET_KEY = os.getenv("SECRET_KEY", hashlib.sha256(str(OWNER_ID).encode()).hexdigest()[:32])

class User:
    def __init__(self, user_id: int, username: str = None, is_active: bool = True, 
                 last_seen: datetime = None, trusted: bool = False):
        self.user_id = user_id
        self.username = username
        self.is_active = is_active
        self.last_seen = last_seen or datetime.now()
        self.trusted = trusted

class Database:
    def __init__(self):
        self.users: Dict[int, User] = {}
        self._load_users()
    
    def _load_users(self):
        if Config.OWNER_ID:
            self.users[Config.OWNER_ID] = User(
                Config.OWNER_ID, 
                is_active=True,
                trusted=True
            )
    
    def add_user(self, user_id: int, username: str = None) -> User:
        if user_id not in self.users:
            self.users[user_id] = User(user_id, username)
            logger.info(f"New user added: {user_id}")
        return self.users[user_id]
    
    def is_authorized(self, user_id: int) -> bool:
        if user_id in Config.ADMIN_IDS:
            return True
        user = self.users.get(user_id)
        return user is not None and user.is_active and user.trusted

db = Database()

class AIModel:
    VISION_MODEL = "models/gemini-2.5-flash"
    
    @classmethod
    def analyze_image(cls, image_data: str, prompt: str = None) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/{cls.VISION_MODEL}:generateContent"
        url += f"?key={Config.GEMINI_KEY}"
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt or "Describe this image in detail"},
                    {"inline_data": {"mime_type": "image/jpeg", "data": image_data}}
                ]
            }]
        }
        
        try:
            response = requests.post(url, json=payload, timeout=60)
            data = response.json()
            
            if 'candidates' in data:
                return data['candidates'][0]['content']['parts'][0]['text']
            
            error_msg = data.get('error', {}).get('message', 'Unknown error')
            logger.error(f"Gemini error: {error_msg}")
            return f"❌ خطأ: {error_msg}"
            
        except Exception as e:
            logger.error(f"Request error: {e}")
            return f"❌ خطأ في الاتصال: {str(e)}"
    
    @classmethod
    def chat(cls, message: str, history: list = None) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/{cls.VISION_MODEL}:generateContent"
        url += f"?key={Config.GEMINI_KEY}"
        
        contents = history or []
        contents.append({"parts": [{"text": message}]})
        
        payload = {"contents": contents}
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            data = response.json()
            
            if 'candidates' in data:
                return data['candidates'][0]['content']['parts'][0]['text']
            
            error_msg = data.get('error', {}).get('message', 'Unknown error')
            return f"❌ خطأ: {error_msg}"
            
        except Exception as e:
            return f"❌ خطأ: {str(e)}"

ai = AIModel()

class MessageHandler:
    @staticmethod
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = db.add_user(update.effective_user.id, update.effective_user.username)
        
        welcome = """
🤖 *MeClaw System*

مرحباً بك في نظام التحكم الذكي!

🔹 *الأوامر المتاحة:*
/help - المساعدة
/ai <رسالة> - الدردشة مع الذكاء الاصطناعي
/image - تحليل الصور
/status - حالة النظام

⚠️ هذا النظام قيد التطوير
"""
        await update.message.reply_text(welcome, parse_mode=ParseMode.MARKDOWN)
    
    @staticmethod
    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not db.is_authorized(update.effective_user.id):
            await update.message.reply_text("⛔ غير مصرح بالوصول")
            return
        
        help_text = """
📚 *دليل الأوامر*

🔹 `/start` - بدء النظام
🔹 `/ai <سؤال>` - سؤال الذكاء الاصطناعي
🔹 `/image` - تحليل الصور (أرسل صورة مع تعليق)
🔹 `/status` - حالة النظام
🔹 `/history` - سجل المحادثات
🔹 `/clear` - مسح السجل

🔐 الأوامر الإدارية:
🔹 `/users` - قائمة المستخدمين
🔹 `/trust <id>` - إضافة مستخدم موثوق
🔹 `/block <id>` - حظر مستخدم
"""
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    @staticmethod
    async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
        status_text = f"""
📊 *حالة النظام*

✅ البوت: يعمل
👥 المستخدمين: {len(db.users)}
🔐 الوضع: آمن
🤖 AI Model: Gemini 2.5 Flash
🕐 الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        await update.message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN)
    
    @staticmethod
    async def handle_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not db.is_authorized(update.effective_user.id):
            await update.message.reply_text("⛔ غير مصرح")
            return
        
        if not context.args:
            await update.message.reply_text("❌ استخدم: /ai <رسالتك>")
            return
        
        message = ' '.join(context.args)
        await update.message.reply_text("🤖 جاري المعالجة...")
        
        response = ai.chat(message)
        
        await MessageHandler.send_long_message(update, response)
    
    @staticmethod
    async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not db.is_authorized(update.effective_user.id):
            await update.message.reply_text("⛔ غير مصرح")
            return
        
        await update.message.reply_text("🖼️ جاري تحليل الصورة...")
        
        try:
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            downloaded = await file.download_as_bytearray()
            image_data = base64.b64encode(downloaded).decode('utf-8')
            
            caption = update.message.caption or "Describe this image"
            
            response = ai.analyze_image(image_data, caption)
            await MessageHandler.send_long_message(update, response)
            
        except Exception as e:
            logger.error(f"Photo error: {e}")
            await update.message.reply_text(f"❌ خطأ: {str(e)}")
    
    @staticmethod
    async def handle_document_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not db.is_authorized(update.effective_user.id):
            return
        
        doc = update.message.document
        if doc.mime_type and doc.mime_type.startswith('image/'):
            await update.message.reply_text("🖼️ جاري تحليل الصورة...")
            try:
                file = await context.bot.get_file(doc.file_id)
                downloaded = await file.download_as_bytearray()
                image_data = base64.b64encode(downloaded).decode('utf-8')
                caption = update.message.caption or "Describe this image"
                response = ai.analyze_image(image_data, caption)
                await MessageHandler.send_long_message(update, response)
            except Exception as e:
                await update.message.reply_text(f"❌ خطأ: {str(e)}")
    
    @staticmethod
    async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not db.is_authorized(update.effective_user.id):
            return
        
        text = update.message.text
        if text.startswith('/'):
            return
        
        await update.message.reply_text("🤖 جاري المعالجة...")
        response = ai.chat(text)
        await MessageHandler.send_long_message(update, response)
    
    @staticmethod
    async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != Config.OWNER_ID:
            await update.message.reply_text("⛔ هذا الأمر للإدارة فقط")
            return
        
        users_list = "👥 *المستخدمون:*\n\n"
        for uid, user in db.users.items():
            status = "✅" if user.is_active else "❌"
            trusted = "🔐" if user.trusted else "👤"
            users_list += f"{status}{trusted} `{uid}` - {user.username or 'No username'}\n"
        
        await update.message.reply_text(users_list, parse_mode=ParseMode.MARKDOWN)
    
    @staticmethod
    async def admin_trust(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != Config.OWNER_ID:
            return
        
        if not context.args:
            await update.message.reply_text("❌ استخدم: /trust <user_id>")
            return
        
        try:
            user_id = int(context.args[0])
            db.add_user(user_id)
            db.users[user_id].trusted = True
            db.users[user_id].is_active = True
            await update.message.reply_text(f"✅ تم اعتماد المستخدم {user_id}")
        except:
            await update.message.reply_text("❌ معرف مستخدم غير صحيح")
    
    @staticmethod
    async def send_long_message(update, text: str):
        if not text:
            return
        for i in range(0, len(text), 4000):
            await update.message.reply_text(text[i:i+4000])

def create_app() -> Application:
    app = Application.builder().token(Config.TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", MessageHandler.start))
    app.add_handler(CommandHandler("help", MessageHandler.help_command))
    app.add_handler(CommandHandler("status", MessageHandler.status))
    app.add_handler(CommandHandler("ai", MessageHandler.handle_ai))
    app.add_handler(CommandHandler("users", MessageHandler.admin_users))
    app.add_handler(CommandHandler("trust", MessageHandler.admin_trust))
    
    app.add_handler(MessageHandler(filters.PHOTO, MessageHandler.handle_photo))
    app.add_handler(MessageHandler(filters.Document.IMAGE, MessageHandler.handle_document_image))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, MessageHandler.handle_text))
    
    return app

def main():
    logger.info("🚀 Starting MeClaw System...")
    
    if not all([Config.TELEGRAM_TOKEN, Config.GEMINI_KEY]):
        logger.error("Missing required environment variables!")
        return
    
    application = create_app()
    
    logger.info("✅ Bot initialized successfully")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
