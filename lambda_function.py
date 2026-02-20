"""
StockMate Lambda Function
Main handler for ETF investment tracking and buy signal generation.

This function coordinates between:
- Google Drive (data storage)
- ETF Analysis (price fetching and trend analysis)
- Telegram (notifications and commands)
"""

import json
import os
import datetime

# Import our custom modules
from google_drive_client import GoogleDriveClient
from telegram_client import TelegramClient
from etf_analysis import get_etf_price, should_buy, backfill_price_history

# Environment variables
ETF_TICKER = os.getenv("ETF_TICKER")
WAIT_PERIOD_DAYS = int(os.getenv("WAIT_PERIOD_DAYS", "30"))
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
GOOGLE_DRIVE_FILE_ID = os.getenv("GOOGLE_DRIVE_FILE_ID")


def handle_telegram_command(event, context):
    """
    Handle Telegram bot commands: /deposit, /bought, /status
    Triggered by Telegram webhook when user sends a message to the bot.
    """
    try:
        print(f"Received Telegram webhook event")
        
        # Parse event based on source (Lambda Function URL vs API Gateway)
        telegram_update = event
        
        # If using Lambda Function URL, body is a JSON string
        if "body" in event and isinstance(event.get("body"), str):
            print("📦 Detected Lambda Function URL format - parsing body")
            telegram_update = json.loads(event["body"])
        
        print(f"Telegram update: {json.dumps(telegram_update)[:300]}...")
        
        # Initialize clients
        gdrive = GoogleDriveClient(GOOGLE_SERVICE_ACCOUNT_JSON, GOOGLE_DRIVE_FILE_ID)
        telegram = TelegramClient(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
        
        # Process the command
        success, response = telegram.process_command(telegram_update, gdrive, WAIT_PERIOD_DAYS)
        
        # Send response to user
        telegram.send_message(response)
        
        # Return success to Telegram (required for webhook)
        # Format for Lambda Function URL
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({"ok": True})
        }
        
    except Exception as e:
        error_msg = f"Error in telegram command handler: {str(e)}"
        print(error_msg)
        try:
            telegram = TelegramClient(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
            telegram.send_message(f"❌ Error: {str(e)}")
        except:
            pass
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({"ok": True, "error": str(e)})
        }


def handle_scheduled_check(event, context):
    """
    Handle scheduled ETF price check (triggered by EventBridge).
    This function runs daily to check ETF prices and determine if it's time to buy.
    """
    try:
        print(f"Starting scheduled ETF check for {ETF_TICKER} at {datetime.datetime.now()}")
        
        # Initialize clients
        gdrive = GoogleDriveClient(GOOGLE_SERVICE_ACCOUNT_JSON, GOOGLE_DRIVE_FILE_ID)
        telegram = TelegramClient(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
        
        # Load data from Google Drive
        print("Loading data from Google Drive...")
        data = gdrive.read_file()
        
        # Ensure status field exists (backward compatibility)
        if "status" not in data:
            data["status"] = "active"
        
        # Check if checking is paused
        if data["status"] == "paused":
            print("⏸️ Checking is PAUSED - waiting for next deposit")
            print("User needs to send /deposit command to resume checking")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Checking paused - waiting for deposit',
                    'status': 'paused'
                })
            }
        
        print("✅ Status is ACTIVE - proceeding with check")
        
        # Get current ETF price
        print(f"Fetching current price for {ETF_TICKER}...")
        current_price = get_etf_price(ETF_TICKER)
        
        if current_price is None:
            error_msg = "Error: Could not fetch ETF price."
            print(error_msg)
            telegram.send_message(f"⚠️ {error_msg}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Could not fetch ETF price'})
            }
        
        # Update today's price
        today_str = str(datetime.date.today())
        data["tracked_prices"][today_str] = current_price

        # Backfill historical prices if the lambda was offline for more than one day.
        # A gap > 1 day means we missed runs; yfinance history fills those dates so
        # analyze_trend has enough data points to produce a buy signal.
        needs_backfill = False
        if len(data["tracked_prices"]) < 5:
            needs_backfill = True
            print("⚠️ Fewer than 5 price entries — backfilling historical data")
        else:
            # Exclude today (just added) and find the second-most-recent date
            previous_dates = sorted(k for k in data["tracked_prices"] if k != today_str)
            if previous_dates:
                last_date = datetime.date.fromisoformat(previous_dates[-1])
                gap_days = (datetime.date.today() - last_date).days
                if gap_days > 1:
                    needs_backfill = True
                    print(f"⚠️ Price history gap of {gap_days} days detected — backfilling")

        if needs_backfill:
            data["tracked_prices"] = backfill_price_history(ETF_TICKER, data["tracked_prices"])

        # Keep only the most recent 30 days of prices, removing all excess at once
        if len(data["tracked_prices"]) > 30:
            sorted_dates = sorted(data["tracked_prices"].keys())
            for old_date in sorted_dates[:-30]:
                del data["tracked_prices"][old_date]
            print(f"Trimmed price history to 30 entries")
        
        print(f"Today's {ETF_TICKER} price: {current_price}")
        
        # Determine if we should buy
        buy_now, reason = should_buy(data, current_price, WAIT_PERIOD_DAYS)
        print(f"[{datetime.date.today()}] {reason}")
        
        # Prepare message with emoji
        if buy_now:
            message = f"✅ BUY SIGNAL\n\n{reason}\n\n💡 When you buy, send: /bought"
            data["last_action"] = f"Buy signal at {current_price}"
        else:
            message = f"⏳ WAIT\n\n{reason}"
            data["last_action"] = "Waiting"
        
        # Send Telegram notification
        telegram.send_message(message)
        
        # Save updated data to Google Drive
        print("Saving data to Google Drive...")
        gdrive.write_file(data)
        
        print("ETF check completed successfully")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'ETF check completed',
                'ticker': ETF_TICKER,
                'price': current_price,
                'buy_signal': buy_now,
                'reason': reason
            })
        }
        
    except Exception as e:
        error_msg = f"Error in scheduled check: {str(e)}"
        print(error_msg)
        
        # Try to send error notification
        try:
            telegram = TelegramClient(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
            telegram.send_message(f"❌ Lambda Error: {str(e)}")
        except:
            pass
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def lambda_handler(event, context):
    """
    Main Lambda handler - routes to appropriate function based on trigger type.
    
    Supports two trigger types:
    1. EventBridge (scheduled) - Daily ETF price checking
    2. Telegram Webhook - Bot commands (/deposit, /bought, /status)
    """
    print(f"Lambda invoked with event: {json.dumps(event)[:500]}...")
    
    # Detect trigger type
    # Check for Lambda Function URL (has "body" field) or direct Telegram webhook
    if "body" in event:
        # Lambda Function URL format
        print("🤖 Detected: Telegram webhook via Function URL")
        return handle_telegram_command(event, context)
    elif "message" in event or "callback_query" in event:
        # Direct Telegram webhook (API Gateway format)
        print("🤖 Detected: Telegram webhook (direct)")
        return handle_telegram_command(event, context)
    else:
        # Triggered by EventBridge or manual test
        print("⏰ Detected: Scheduled check trigger")
        return handle_scheduled_check(event, context)


# For local testing
if __name__ == "__main__":
    # Simulate Lambda event and context
    result = lambda_handler({}, None)
    print(json.dumps(result, indent=2))
