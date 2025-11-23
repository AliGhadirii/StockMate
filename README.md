# StockMate - ETF Investment Tracker

Automated ETF investment advisor that runs on AWS Lambda and sends recommendations via Telegram.

## 🚀 Quick Start - AWS Lambda Deployment

This repository is structured for easy deployment to AWS Lambda using the AWS Console.

### Repository Structure

```
StockMate/
├── lambda_function.py          # Main Lambda handler (DO NOT RENAME)
├── lambda_requirements.txt     # Lambda dependencies
├── lambda_env_template.txt     # Environment variable template
├── get_google_drive_token.py   # Utility to get Google Drive credentials
├── LICENSE                     # MIT License
├── README.md                   # This file
└── local_dev/                  # Local development version (not deployed)
    ├── main.py                 # CLI version for local testing
    ├── utils.py                # Local utilities
    ├── requirements.txt        # Local dependencies
    └── Data/                   # Local data storage
```

### Prerequisites

1. **AWS Account** with appropriate permissions
2. **Python 3.11+** installed locally
3. **Google Cloud Project** with Drive API enabled
4. **Telegram Bot** created via @BotFather

### Setup Instructions

#### Step 1: Set Up Google Drive Service Account

Follow the detailed guide: **`SERVICE_ACCOUNT_SETUP.md`**

Quick summary:
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a Service Account
3. Download the JSON key file
4. Enable Google Drive API
5. Create `investment_data.json` in your Google Drive
6. Share the file with your service account email (Editor access)

#### Step 2: Build Deployment Package

1. **Run the build script**:
   - **Windows**: Double-click `build_lambda.bat`
   - **Mac/Linux**: Run `bash build_lambda.sh`

2. **Result**: Creates `lambda_deployment.zip` (ready to upload)

The script will:
- Install all dependencies (yfinance, pandas, numpy, requests)
- Package everything with your Lambda function
- Create a zip file ready for AWS

#### Step 3: Create Lambda Function in AWS Console

1. **Go to AWS Lambda Console**: https://console.aws.amazon.com/lambda

2. **Click "Create function"**

3. **Basic Information**:
   - Select: **"Author from scratch"**
   - Function name: `stockmate-etf-checker` (or your choice)
   - Runtime: **Python 3.11** (recommended) or Python 3.12
   - Architecture: **x86_64** (recommended - better package compatibility)
     - ⚠️ Do NOT use arm64 unless you rebuild dependencies for ARM

4. **Permissions** (Execution role):
   - Select: **"Create a new role with basic Lambda permissions"**
   - This creates a role with CloudWatch Logs permissions (needed for logging)
   - Role name will be auto-generated: `stockmate-etf-checker-role-xxxxx`

5. **Advanced settings** (expand):
   - ✅ **Enable function URL**: Leave UNCHECKED (not needed)
   - ✅ **VPC**: Leave as **"No VPC"** ⚠️ IMPORTANT (see networking section below)

6. **Click "Create function"**

#### Step 4: Upload Deployment Package

1. In your Lambda function page, go to the **Code** tab

2. **Upload your package**:
   - Click **"Upload from"** → **".zip file"**
   - Click **"Upload"** button
   - Select `lambda_deployment.zip`
   - Click **"Save"**

3. **Wait** for upload to complete (may take 30-60 seconds for large packages)

4. **Verify**:
   - You should see `lambda_function.py` in the code editor
   - Handler should show: `lambda_function.lambda_handler`
   - If handler is wrong, go to **Runtime settings** → **Edit** → Set handler to: `lambda_function.lambda_handler`

#### Step 5: Configure Function Settings

Go to **Configuration** tab and configure the following:

##### 5.1 General Configuration

Click **General configuration** → **Edit**:
- **Memory**: `256 MB` (minimum for pandas/numpy)
  - Can increase to 512 MB if you get memory errors
- **Timeout**: `1 minute` (60 seconds)
  - Sufficient for API calls and data processing
- **Ephemeral storage**: `512 MB` (default is fine)
- Click **Save**

##### 5.2 Environment Variables

Click **Environment variables** → **Edit** → **Add environment variable**

Add all of these (5 total):

| Key | Value | Example |
|-----|-------|---------|
| `ETF_TICKER` | Your ETF symbol | `VOO` or `IVV.AX` |
| `WAIT_PERIOD_DAYS` | Max days before buy | `30` |
| `TELEGRAM_BOT_TOKEN` | From @BotFather | `123456789:ABCdef...` |
| `TELEGRAM_CHAT_ID` | From @userinfobot | `123456789` |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Service account JSON | `{"type":"service_account",...}` |
| `GOOGLE_DRIVE_FILE_ID` | Drive file ID | `1AbCdEf...` |

Click **Save** after adding all variables.

**📝 Note**: See `lambda_env_template.txt` for detailed descriptions and how to get each value.

##### 5.3 Networking Configuration ⚠️ IMPORTANT

**DO NOT configure VPC settings!**

Go to **VPC** section and verify:
- **VPC**: Shows "No VPC"
- **Subnets**: Empty
- **Security groups**: Empty

**Why no VPC?**
- By default, Lambda runs in an AWS-managed VPC with internet access
- Your function needs to call external APIs:
  - Telegram API (`api.telegram.org`)
  - Google Drive API (`googleapis.com`)
  - Yahoo Finance (via yfinance)
- If you add a custom VPC, Lambda loses internet access unless you add NAT Gateway (costs $$$)
- **Leave VPC settings empty** for automatic internet access ✅

**✅ Correct Configuration**: No VPC (default)
- Lambda has automatic internet access
- Can call all external APIs
- No additional networking costs

**❌ Wrong Configuration**: Custom VPC without NAT
- Lambda cannot reach internet
- API calls will fail
- You'll get timeout errors

##### 5.4 Monitoring and Logging

**CloudWatch Logs** (automatic):
- Lambda automatically creates log group: `/aws/lambda/stockmate-etf-checker`
- All `print()` statements go to CloudWatch Logs
- Logs are automatically created - no configuration needed
- Retention: Default 7 days (can change in CloudWatch Logs console)

**Insights** (optional):
- Go to **Monitoring** tab to see:
  - Invocations
  - Duration
  - Error count
  - Throttles

#### Step 6: Test Your Function (Before Adding Trigger)

**Test manually first** to make sure everything works:

1. Go to **Test** tab

2. **Create test event**:
   - Click **"Create new event"**
   - Event name: `test-etf-check`
   - Template: Leave as default (hello-world)
   - Event JSON: Use empty object:
     ```json
     {}
     ```
   - Click **"Save"**

3. **Run the test**:
   - Click **"Test"** button
   - Wait for execution (may take 10-30 seconds)

4. **Check results**:
   - **✅ Success**: You'll see green banner "Execution result: succeeded"
   - View response in **Execution results** section
   - Check **Log output** for print statements
   - You should receive a Telegram message!

5. **If it fails**:
   - Check **Error** message
   - Click **CloudWatch Logs** link to see detailed logs
   - Common issues:
     - Wrong environment variables
     - Invalid Telegram token
     - Google Drive credentials expired
     - Network timeout (check VPC settings)

#### Step 7: Add Scheduled Trigger (Automate Daily Execution)

Once testing works, add a trigger for daily automatic execution:

1. In your Lambda function, go to **Function overview** section

2. Click **"Add trigger"**

3. **Select a trigger**: Choose **EventBridge (CloudWatch Events)**

4. **Configure trigger**:
   - **Rule**: Select **"Create a new rule"**
   - **Rule name**: `daily-etf-check`
   - **Rule description**: "Runs StockMate ETF checker daily"
   - **Rule type**: **Schedule expression**
   
5. **Schedule expression** (choose one):
   
   **Option A - Cron expression** (for specific time):
   ```
   cron(0 13 * * ? *)
   ```
   - Runs daily at 1:00 PM UTC
   - Change hour for your timezone:
     - `cron(0 9 * * ? *)` = 9 AM UTC
     - `cron(30 14 * * ? *)` = 2:30 PM UTC
   - Format: `cron(minute hour day month day-of-week year)`
   - Note: Uses UTC time, not your local time
   
   **Option B - Rate expression** (simpler):
   ```
   rate(1 day)
   ```
   - Runs once per day (24 hours after last run)
   - Simpler but less precise timing

6. **Enable trigger**: Check **"Enable trigger"**

7. Click **"Add"**

**Verify trigger**:
- You should see EventBridge trigger in **Function overview** diagram
- Trigger status should be "Enabled"

**To modify schedule**:
- Go to **Configuration** → **Triggers**
- Click the trigger name
- Opens EventBridge console where you can edit the rule

#### Step 8: Monitor Your Function

**CloudWatch Logs**:
1. Go to **Monitor** tab in Lambda console
2. Click **"View CloudWatch logs"**
3. Click latest log stream to see execution details
4. Look for:
   - ETF price fetched
   - Buy/wait decision
   - Telegram message sent
   - Google Drive updated

**CloudWatch Metrics**:
- Go to **Monitor** tab
- See graphs for:
   - Invocations (should be 1/day)
   - Duration (should be 10-30 seconds)
   - Errors (should be 0)
   - Throttles (should be 0)

**Set up Alarms** (optional):
1. Go to CloudWatch Console
2. Create alarm for Lambda errors
3. Get notified if function fails

---

## Additional Information

### How It Works

1. Lambda runs on schedule (e.g., daily)
2. Fetches current ETF price from Yahoo Finance
3. Analyzes price trends and timing
4. Determines if it's a good time to buy based on:
   - Dynamic price threshold (volatility-adjusted)
   - Maximum wait period
5. Sends Telegram notification with recommendation
6. Stores data in Google Drive for persistence

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `ETF_TICKER` | ETF symbol to track | `VOO`, `VTI`, `SPY` |
| `WAIT_PERIOD_DAYS` | Max days before forced buy | `30` |
| `TELEGRAM_BOT_TOKEN` | From @BotFather | `123456:ABC...` |
| `TELEGRAM_CHAT_ID` | From @userinfobot | `123456789` |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Service account JSON key | `{"type":"service_account",...}` |
| `GOOGLE_DRIVE_FILE_ID` | JSON file ID | `1AbC...` |

### Security Notes

⚠️ **NEVER commit secrets to Git!**
- All credentials should be stored as Lambda environment variables
- The `.gitignore` is configured to prevent accidental commits
- Keep your Google Drive credentials and Telegram token secure

### AWS Lambda Configuration Summary

| Setting | Value | Why |
|---------|-------|-----|
| **Runtime** | Python 3.11 | Latest stable Python for Lambda |
| **Architecture** | x86_64 | Best package compatibility |
| **Memory** | 256 MB | Enough for pandas/numpy |
| **Timeout** | 60 seconds | Enough for API calls |
| **VPC** | No VPC | Automatic internet access |
| **Handler** | `lambda_function.lambda_handler` | Entry point |
| **Execution role** | Auto-created | CloudWatch Logs permissions |
| **Trigger** | EventBridge (daily) | Scheduled execution |

### Networking Explained

**Your Lambda needs internet access** to call:
- ✅ Telegram API (`api.telegram.org`)
- ✅ Google Drive API (`www.googleapis.com`)
- ✅ Yahoo Finance (via yfinance library)

**Default Setup (Recommended)** ✅:
- VPC: **No VPC**
- Lambda runs in AWS-managed VPC
- Has automatic internet access
- No additional cost
- No configuration needed

**Custom VPC (NOT Recommended)** ❌:
- If you configure a custom VPC, Lambda loses internet access
- You'd need to add:
  - NAT Gateway (~$33/month)
  - Internet Gateway
  - Route tables
  - Security groups
- Complex and expensive
- **Don't do this unless you know why you need it**

**Security**:
- Lambda has outbound internet access (can make requests)
- Lambda has NO inbound internet access (cannot be called from internet without Function URL)
- Your secrets are in environment variables (encrypted at rest)
- IAM role controls what AWS services Lambda can access

### Costs

**Monthly Cost Estimate** (within free tier):

| Service | Usage | Free Tier | Cost |
|---------|-------|-----------|------|
| **Lambda Requests** | 30 invocations/month | 1M requests | $0.00 |
| **Lambda Duration** | 30 × 20 sec = 10 min | 400,000 GB-seconds | $0.00 |
| **CloudWatch Logs** | ~1 MB/month | 5 GB ingestion | $0.00 |
| **EventBridge** | 30 events/month | 1M events | $0.00 |
| **Google Drive API** | 60 API calls/month | Unlimited | $0.00 |
| **Data Transfer** | ~10 MB/month | 1 GB outbound | $0.00 |
| **Total** | | | **$0.00** |

**✅ This project costs $0/month** (well within free tier limits)

### Troubleshooting

#### "Could not fetch ETF price"
- ✅ Check ETF ticker is correct (e.g., `VOO`, `VTI`, `IVV.AX`)
- ✅ Check Lambda has internet access (VPC should be "No VPC")
- ✅ Check CloudWatch Logs for detailed error
- ✅ Try testing with a known ticker like `VOO` or `SPY`

#### "Task timed out after 60.00 seconds"
- ✅ Increase timeout: Configuration → General → Timeout → 2 minutes
- ✅ Check if API endpoints are slow (check CloudWatch Logs)
- ✅ May be temporary network issue - try again

#### "Google Drive error" / "401 Unauthorized"  
- ✅ Verify service account JSON is correctly formatted
- ✅ Check that Drive API is enabled in Google Cloud Console
- ✅ Ensure the Drive file is shared with your service account email
- ✅ Verify file ID is correct (from Drive file URL)

#### "Telegram message failed"
- ✅ Verify bot token format: `123456789:ABCdef...`
- ✅ Check chat ID is numeric: `123456789`
- ✅ Start a chat with your bot first (send `/start` in Telegram)
- ✅ Check bot token hasn't been revoked in @BotFather

#### "Unable to import module 'lambda_function'" / "No module named 'pandas'"
- ❌ Dependencies not included in zip
- ✅ Re-run `build_lambda.bat` to rebuild package
- ✅ Verify `lambda_deployment.zip` includes dependencies
- ✅ Check Runtime is Python 3.11 (not 3.9 or 3.10)

#### "Memory Size: 256 MB Max Memory Used: 250 MB"
- ⚠️ Close to memory limit
- ✅ Increase memory: Configuration → General → Memory → 512 MB

#### No logs in CloudWatch
- ✅ Check Lambda execution role has CloudWatch Logs permissions
- ✅ Go to IAM Console → Roles → (your lambda role) → Should have `AWSLambdaBasicExecutionRole` policy

#### Function works in test but not with EventBridge trigger
- ✅ Check EventBridge rule is enabled
- ✅ Check trigger is added to Lambda
- ✅ Wait for next scheduled time
- ✅ Check CloudWatch Logs around scheduled time

#### "Network is unreachable" / API timeouts
- ❌ Lambda is in custom VPC without internet access
- ✅ Go to Configuration → VPC → Edit → Select "No VPC"
- ✅ Save and test again

### Support

For issues or questions, please open an issue on GitHub.

### License

MIT License - See LICENSE file for details

