# MeClaw System - دليل التثبيت

## 🎯 نظرة عامة
نظام متكامل للتحكم بالذكاء الاصطناعي عبر Telegram

## ⚡ الميزات
- 🤖 دردشة مع Gemini AI
- 🖼️ تحليل الصور
- 🔐 نظام أمان متقدم
- 👥 إدارة المستخدمين
- 📊 لوحة تحكم

## 🔧 التثبيت على Railway

### 1. ربط GitHub
1. أنشئ حساب على [railway.app](https://railway.app)
2. اضغط **New Project** → **Deploy from GitHub**
3. اختر repo `nnfoolder`

### 2. Environment Variables
أضف في Railway:
```
TELEGRAM_TOKEN = your_bot_token
GEMINI_KEY = your_gemini_api_key
OWNER_ID = your_telegram_user_id
```

### 3. الحصول على Telegram Token
1. تحدث مع [@BotFather](https://t.me/BotFather)
2. أرسل `/newbot`
3. اتبع الخطوات واحفظ الـ token

### 4. الحصول على USER ID
1. تحدث مع [@userinfobot](https://t.me/userinfobot)
2. انسخ الـ ID

### 5. الحصول على Gemini API Key
1. اذهب لـ [aistudio.google.com](https://aistudio.google.com)
2. أنشئ API key جديد
3. ⚠️ لا تنشره أبداً!

## 📱 الأوامر المتاحة

| الأمر | الوصف |
|-------|-------|
| `/start` | بدء النظام |
| `/help` | المساعدة |
| `/status` | حالة النظام |
| `/ai <سؤال>` | سؤال AI |
| `/users` | قائمة المستخدمين (للمدير) |
| `/trust <id>` | اعتماد مستخدم (للمدير) |

## 🔒 الأمان
- ✅ API keys في متغيرات البيئة فقط
- ✅ نظام موثوقية المستخدمين
- ✅ تشفير البيانات
- ✅ صلاحيات متعددة المستويات

## 🌐 API Endpoints
```
GET  /health - فحص النظام
GET  /status - حالة API
POST /ai - سؤال الذكاء الاصطناعي
POST /image - تحليل صورة
```

## 📞 الدعم
للمساعدة أو الإبلاغ عن مشاكل
