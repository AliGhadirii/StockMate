# Quick Setup Checklist - Telegram Bot Commands

Use this as a quick reference while setting up. See `TELEGRAM_BOT_SETUP.md` for detailed instructions.

## ✅ Step-by-Step Checklist

### □ **Step 0: Register Bot Commands** (1 minute) - Optional

1. Open Telegram → Find @BotFather
2. Send: `/setcommands`
3. Select your bot
4. Send this list:
```
deposit - Start new investment cycle with amount
bought - Confirm you bought ETF (pauses checking)
status - View current status and settings
help - Show available commands
```

This makes commands appear in Telegram's "/" menu (optional but recommended).

---

### □ **Step 1: Update Google Drive JSON** (2 minutes)

1. Open `investment_data.json` in Google Drive
2. Add `"status": "active"` field (or "paused")
3. Save the file

```json
{
    "status": "active",
    "last_deposit_date": "2025-11-23",
    "deposit_amount": 3700.0,
    ...
}
```

---

### □ **Step 2: Deploy Updated Lambda** (3 minutes)

1. Run build script:
   - Windows: `build_lambda.bat`
   - Mac/Linux: `bash build_lambda.sh`

2. Upload to Lambda:
   - AWS Console → Lambda → Your function
   - Code tab → Upload from .zip file
   - Select `lambda_deployment.zip`
   - Wait for upload

3. Test it:
   - Test tab → Click Test
   - Check it runs without errors

---

### □ **Step 3: Enable Function URL** (2 minutes)

1. Lambda Console → Configuration → Function URL
2. Click "Create function URL"
3. Auth type: **NONE**
4. Save
5. **COPY THE URL** (save it for next step!)

Example URL:
```
https://abc123xyz.lambda-url.us-east-1.on.aws/
```

---

### □ **Step 4: Set Telegram Webhook** (1 minute)

**Replace placeholders and open this URL in your browser:**

```
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=<YOUR_LAMBDA_URL>
```

**Example:**
```
https://api.telegram.org/bot123456789:ABCdefGHIjklMNOpqrsTUVwxyz/setWebhook?url=https://abc123xyz.lambda-url.us-east-1.on.aws/
```

**Expected response:**
```json
{"ok":true,"result":true,"description":"Webhook was set"}
```

✅ If you see this, webhook is configured!

---

### □ **Step 5: Test Bot Commands** (2 minutes)

Open Telegram and test each command:

```
/start         → Should show help
/status        → Should show current status  
/deposit 3700  → Should activate checking
/bought        → Should pause checking
```

---

## 🎯 Done!

Your bot is now interactive! Use it like this:

1. **Deposit money** → Send: `/deposit 3700`
2. **Wait for signals** (bot checks daily automatically)
3. **Get buy signal** → Buy as many ETFs as possible
4. **Confirm purchase** → Send: `/bought`
5. **Bot pauses** until next deposit
6. **Repeat!**

---

## 🔍 Quick Verify

### Check webhook is working:
```
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo
```

Should show your Lambda URL.

### Check Lambda logs:
- Lambda → Monitor → View CloudWatch logs
- Send a command and watch logs appear

---

## 📚 Full Documentation

- **Detailed Setup:** See `TELEGRAM_BOT_SETUP.md`
- **Troubleshooting:** See section in `TELEGRAM_BOT_SETUP.md`
- **Architecture:** See `README.md`

---

## 🆘 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| Bot doesn't respond | Check webhook with getWebhookInfo |
| "Unauthorized" error | Verify TELEGRAM_CHAT_ID matches your ID |
| Scheduled checks stopped | Status is "paused", send /deposit to resume |
| JSON errors | Check Google Drive permissions |

---

## 🎉 Total Time: ~10 minutes

Questions? Check `TELEGRAM_BOT_SETUP.md` for detailed help!

