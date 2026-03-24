# MeClaw Telegram Bot - Neural Network Folder
# Secure AI-powered Telegram bot with Railway deployment

## Features
- AI-powered responses using Gemini
- Webhook-based (no polling)
- Secure environment variable storage
- IP blocking support
- Health check endpoint

## Setup

### 1. Railway Deployment
1. Create account at https://railway.app
2. Connect your GitHub repository
3. Add Environment Variables:
   - `TELEGRAM_TOKEN`: Your bot token from @BotFather
   - `GEMINI_KEY`: Your Gemini API key
   - `OWNER_ID`: Your Telegram user ID
   - `WEBHOOK_HOST`: Your Railway app URL (e.g., https://mybot.railway.app)
   - `WEBHOOK_SECRET`: Generate with: openssl rand -hex 32
   - `PORT`: 8000

### 2. Set Webhook
After deployment, run:
```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -d "url=https://your-app.railway.app/webhook" \
  -d "secret_token=YOUR_WEBHOOK_SECRET"
```

### 3. Get Your Telegram ID
Message @userinfobot on Telegram to get your ID.

## Security Features
- API keys stored in environment variables (never in code)
- Webhook verification with secret token
- IP blocking capability
- Non-root container user
