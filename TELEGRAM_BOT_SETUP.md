# Telegram Bot Setup Guide - Interactive Commands

## 📋 Overview

This guide will help you set up interactive Telegram bot commands so you can:
- `/deposit <amount>` - Start a new investment cycle
- `/bought` - Record a purchase and pause checking
- `/status` - View current status
- `/help` - Get help

## 🎯 Workflow After Setup

```
You: /deposit 3700
Bot: ✅ Deposit recorded! I'll check daily for best buy time.

[Bot checks daily and sends signals when status is "active"]

Day 25: Bot: ✅ BUY SIGNAL - Price dipped to $68.20!
Day 26: Bot: ✅ BUY SIGNAL - Still a good buy!

[You buy as many ETFs as possible with your $3700]

You: /bought
Bot: ✅ Purchase recorded! Paused until next deposit.

[Bot stays silent until you deposit again]

You: /deposit 3700
Bot: ✅ Deposit recorded! Daily checking enabled.

[Cycle repeats...]
```

---

## 📝 Step-by-Step Setup Instructions

### **Step 0: Register Bot Commands with BotFather** (Optional but Recommended)

This step makes the commands appear in Telegram's UI when you type "/".

1. **Open Telegram** and find **@BotFather**

2. **Send this message:**
   ```
   /setcommands
   ```

3. **Select your bot** from the list

4. **Send this command list** (copy and paste exactly):
   ```
   deposit - Start new investment cycle with amount
   bought - Confirm you bought ETF (pauses checking)
   status - View current status and settings
   help - Show available commands
   ```

5. **Done!** Now when you type "/" in your bot chat, these commands will appear in a menu.

**Note:** This step is optional. The commands will work even if you skip this, but having them in the menu makes the bot easier to use.

---

### **Step 1: Update Your Google Drive JSON**

1. Open your `investment_data.json` file in Google Drive

2. Add a `"status"` field to the JSON:

**Before:**
```json
{
    "last_deposit_date": "2025-10-30",
    "deposit_amount": 3700.0,
    "tracked_prices": {...},
    "last_action": "..."
}
```

**After:**
```json
{
    "status": "active",
    "last_deposit_date": "2025-10-30",
    "deposit_amount": 3700.0,
    "tracked_prices": {...},
    "last_action": "..."
}
```

3. Set `"status"` to:
   - `"active"` - If you have money deposited and want daily checks
   - `"paused"` - If you've already bought and waiting for next deposit

4. **Save the file**

**Note:** If you skip this step, the code will automatically add `"status": "active"` for backward compatibility.

---

### **Step 2: Deploy Updated Lambda Code**

1. **Rebuild your deployment package:**

   **Windows:**
   ```cmd
   build_lambda.bat
   ```

   **Mac/Linux:**
   ```bash
   bash build_lambda.sh
   ```

2. **Upload to Lambda:**
   - Go to [AWS Lambda Console](https://console.aws.amazon.com/lambda)
   - Open your `stockmate-etf-checker` function
   - Go to **Code** tab
   - Click **Upload from** → **.zip file**
   - Select `lambda_deployment.zip`
   - Click **Save**
   - Wait for upload to complete

3. **Test the updated function:**
   - Go to **Test** tab
   - Click **Test** button
   - Check CloudWatch logs to verify it works

---

### **Step 3: Enable Lambda Function URL**

Your Lambda needs a public URL so Telegram can send webhook requests to it.

1. **In Lambda Console**, go to your function

2. Click **Configuration** tab

3. Click **Function URL** in the left sidebar

4. Click **Create function URL**

5. **Configure:**
   - **Auth type**: Select **NONE** ⚠️
     - This is safe because we verify the chat ID in code
     - Only your Telegram user can execute commands
   
6. Click **Save**

7. **Copy the Function URL** - it looks like:
   ```
   https://abc123xyz.lambda-url.us-east-1.on.aws/
   ```

8. **Save this URL** - you'll need it in the next step!

**Security Note:** Even though auth is NONE, the Lambda code checks that commands come from YOUR Telegram chat ID only. Unauthorized users will be rejected.

---

### **Step 4: Set Telegram Webhook**

Tell Telegram to send messages to your Lambda URL.

#### **Method A: Using Web Browser (Easiest)**

1. **Open this URL in your browser** (replace placeholders):

```
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=<YOUR_LAMBDA_URL>
```

**Example:**
```
https://api.telegram.org/bot123456789:ABCdefGHIjklMNOpqrsTUVwxyz/setWebhook?url=https://abc123xyz.lambda-url.us-east-1.on.aws/
```

2. **You should see:**
```json
{"ok":true,"result":true,"description":"Webhook was set"}
```

3. **✅ Done!** Your webhook is configured.

#### **Method B: Using curl (Command Line)**

```bash
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "<YOUR_LAMBDA_URL>"}'
```

---

### **Step 5: Test Your Bot Commands**

1. **Open Telegram** and find your bot

2. **Send: `/start`**
   - Bot should reply with help message

3. **Send: `/status`**
   - Bot should show current status

4. **Send: `/deposit 3700`**
   - Bot should confirm deposit and activate checking

5. **Send: `/bought 69.50`**
   - Bot should confirm purchase and pause checking

6. **Check CloudWatch Logs:**
   - Go to Lambda → Monitor → View CloudWatch logs
   - You should see logs for each command

**✅ If everything works, you're done!**

---

## 🔧 Troubleshooting

### "Bot doesn't respond to commands"

**Check 1: Is webhook set correctly?**
```
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo
```

Should show:
```json
{
  "ok": true,
  "result": {
    "url": "https://abc123.lambda-url.us-east-1.on.aws/",
    "has_custom_certificate": false,
    "pending_update_count": 0
  }
}
```

**Check 2: Is Function URL enabled?**
- Lambda → Configuration → Function URL
- Should show a URL

**Check 3: Is TELEGRAM_CHAT_ID correct?**
- Message [@userinfobot](https://t.me/userinfobot) on Telegram
- Compare the ID with your Lambda environment variable

**Check 4: Check Lambda logs**
- Lambda → Monitor → View CloudWatch logs
- Look for error messages

---

### "Unauthorized" error

**Problem:** Your chat ID doesn't match the environment variable.

**Solution:**
1. Get your chat ID from [@userinfobot](https://t.me/userinfobot)
2. Update Lambda environment variable:
   - Configuration → Environment variables → Edit
   - Update `TELEGRAM_CHAT_ID`
   - Save

---

### "Bot responds but doesn't update JSON"

**Check Google Drive permissions:**
- Verify the Drive file is shared with your service account email
- Service account needs Editor permissions (not just Viewer)
- Check Lambda logs for detailed Google Drive error messages
- Ensure `GOOGLE_SERVICE_ACCOUNT_JSON` is valid JSON format

---

### "Scheduled checks stopped working"

**Did you set status to "paused"?**
- Send `/status` to check
- If paused, send `/deposit <amount>` to resume

---

## 📱 Available Commands Reference

| Command | Usage | Description |
|---------|-------|-------------|
| `/start` | `/start` | Show welcome message and help |
| `/help` | `/help` | Show available commands |
| `/status` | `/status` | View current status, price, and settings |
| `/deposit` | `/deposit 3700` | Start new cycle with amount to invest |
| `/bought` | `/bought` | Confirm purchase (no parameters needed) |

---

## 🔄 Typical Workflow

### **Phase 1: Deposit Money**
```
You: /deposit 3700
Bot: ✅ Deposit Recorded!
     Amount: $3,700.00
     Status: 🟢 ACTIVE
     Daily price checking is now enabled.
```

### **Phase 2: Daily Checks (Automatic)**
- Bot checks price every day at scheduled time
- Sends BUY signals when conditions are met
- You can check anytime with `/status`

### **Phase 3: You Buy the ETF**
```
[You buy as many ETFs as possible with all your deposited money]

You: /bought
Bot: ✅ Purchase Recorded!
     Days waited: 25
     Invested: $3,700.00
     Status: 🔴 PAUSED
     Price checking is now paused.
```

### **Phase 4: Paused**
- Bot stops sending daily messages
- No checking happens
- You deposit more money when ready

### **Phase 5: Next Deposit**
```
You: /deposit 3700
Bot: ✅ Deposit Recorded!
     Cycle starts again...
```

---

## 🔐 Security Notes

1. **Function URL has no auth** - This is intentional
   - Lambda code verifies chat ID
   - Only your Telegram account can execute commands

2. **Keep your bot token secret**
   - Don't share it
   - Don't commit it to git

3. **Chat ID verification**
   - Every command checks if sender matches your chat ID
   - Unauthorized users get rejected

---

## 🎉 You're All Set!

Your bot now has interactive commands! 

**Next steps:**
1. ✅ Test all commands
2. ✅ Send `/deposit` to start tracking
3. ✅ Wait for buy signals
4. ✅ Send `/bought` when you purchase
5. ✅ Repeat!

Enjoy your automated ETF investment tracking! 📈

