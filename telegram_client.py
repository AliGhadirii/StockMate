"""
Telegram Client for StockMate
Handles all Telegram API interactions including sending messages and processing commands.
"""

import requests
import datetime
from typing import Dict, Tuple


class TelegramClient:
    """Client for Telegram Bot API operations."""
    
    def __init__(self, bot_token: str, chat_id: str):
        """Initialize Telegram client.
        
        Args:
            bot_token: Telegram bot token from @BotFather
            chat_id: Telegram chat ID to send messages to
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        
        if not bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        if not chat_id:
            raise ValueError("TELEGRAM_CHAT_ID is required")
    
    def send_message(self, message: str) -> bool:
        """Send a message to the configured Telegram chat.
        
        Args:
            message: Text message to send
            
        Returns:
            True if message sent successfully, False otherwise
        """
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {"chat_id": self.chat_id, "text": message}
            response = requests.post(url, data=payload)
            response.raise_for_status()
            print(f"✅ Telegram message sent successfully")
            return True
        except Exception as e:
            print(f"❌ Error sending Telegram message: {e}")
            return False
    
    def process_command(self, event: Dict, gdrive_client, wait_period_days: int) -> Tuple[bool, str]:
        """Process incoming Telegram bot command.
        
        Args:
            event: Telegram webhook event
            gdrive_client: GoogleDriveClient instance for reading/writing data
            wait_period_days: Maximum wait period setting
            
        Returns:
            Tuple of (success: bool, response_message: str)
        """
        try:
            # Parse Telegram message
            message = event.get("message", {})
            chat_id = message.get("chat", {}).get("id")
            text = message.get("text", "").strip()
            user_name = message.get("from", {}).get("first_name", "User")
            
            if not chat_id:
                print("⚠️ No chat_id found in message")
                return False, "No chat ID found"
            
            # Verify it's from the authorized user
            if str(chat_id) != str(self.chat_id):
                print(f"⚠️ Unauthorized user: {chat_id} (expected {self.chat_id})")
                return False, "❌ Unauthorized. This bot is private."
            
            print(f"Processing command from {user_name}: {text}")
            
            # Parse command first
            parts = text.split()
            raw_command = parts[0].lower() if parts else ""
            
            # Strip bot username if present (e.g., /help@botname -> /help)
            command = raw_command.split('@')[0]
            
            # Debug: Log what command was detected
            print(f"📝 Raw command: '{raw_command}' → Parsed: '{command}'")
            print(f"📝 Full text: '{text}'")
            
            # === COMMAND: /help or /start (No Drive access needed) ===
            if command == "/help" or command == "/start":
                print(f"✅ Matched /help or /start command")

                response = (
                    f"🤖 StockMate Bot Commands\n\n"
                    f"/deposit <amount> - Start new investment cycle\n"
                    f"   Example: /deposit 3700\n"
                    f"   Tell bot you have money to invest\n\n"
                    f"/bought - Confirm you bought ETF\n"
                    f"   Use after you buy with all your deposited money\n"
                    f"   No parameters needed!\n\n"
                    f"/status - View current status\n\n"
                    f"/help - Show this help\n\n"
                    f"💡 Simple Workflow:\n"
                    f"1. You deposit $3700 → /deposit 3700\n"
                    f"2. Bot checks daily for best buy time\n"
                    f"3. Bot sends buy signal when ready\n"
                    f"4. You buy as many ETFs as possible\n"
                    f"5. You confirm → /bought\n"
                    f"6. Bot pauses until you deposit again"
                )
                return True, response
            
            # Load current data (needed for other commands)
            print("Loading data from Google Drive...")
            data = gdrive_client.read_file()
            
            # Ensure status field exists (backward compatibility)
            if "status" not in data:
                data["status"] = "active"
            
            # === COMMAND: /deposit ===
            if command == "/deposit":
                if len(parts) < 2:
                    return False, "❌ Usage: /deposit <amount>\nExample: /deposit 3700"
                
                try:
                    amount = float(parts[1])
                    # Reset cycle and activate checking
                    data["status"] = "active"
                    data["last_deposit_date"] = str(datetime.date.today())
                    data["deposit_amount"] = amount
                    data["last_action"] = f"Deposit recorded: ${amount:,.2f}"
                    
                    gdrive_client.write_file(data)
                    
                    response = (
                        f"✅ Deposit Recorded!\n\n"
                        f"Amount: ${amount:,.2f}\n"
                        f"Date: {datetime.date.today()}\n"
                        f"Status: 🟢 ACTIVE\n\n"
                        f"Daily price checking is now enabled.\n"
                        f"You'll receive buy signals when opportunities arise.\n\n"
                        f"When you buy, just send: /bought"
                    )
                    print(f"✅ Deposit recorded: ${amount}")
                    return True, response
                except ValueError:
                    return False, "❌ Invalid amount. Please enter a number.\nExample: /deposit 3700"
            
            # === COMMAND: /bought ===
            elif command == "/bought":
                purchase_date = str(datetime.date.today())
                
                # Get current price from tracked prices (latest entry)
                latest_price = 0
                if data.get("tracked_prices"):
                    latest_date = max(data["tracked_prices"].keys())
                    latest_price = data["tracked_prices"][latest_date]
                
                # Calculate days since deposit
                if data.get("last_deposit_date"):
                    last_date = datetime.datetime.strptime(data["last_deposit_date"], "%Y-%m-%d").date()
                    days_waited = (datetime.date.today() - last_date).days
                else:
                    days_waited = 0
                
                # Record purchase and pause checking
                data["status"] = "paused"
                data["last_action"] = f"Purchased ETF on {purchase_date}"
                
                gdrive_client.write_file(data)
                
                response = (
                    f"✅ Purchase Recorded!\n\n"
                    f"Date: {purchase_date}\n"
                    f"Days waited: {days_waited}\n"
                    f"Latest tracked price: ${latest_price:.2f}\n"
                    f"Invested: ${data.get('deposit_amount', 0):,.2f}\n"
                    f"Status: 🔴 PAUSED\n\n"
                    f"Price checking is now paused.\n"
                    f"Use /deposit <amount> when you add more funds."
                )
                print(f"✅ Purchase recorded on {purchase_date} (waited {days_waited} days)")
                return True, response
            
            # === COMMAND: /status ===
            elif command == "/status":
                current_status = data.get("status", "unknown")
                last_deposit = data.get("last_deposit_date", "N/A")
                deposit_amount = data.get("deposit_amount", 0)
                last_action = data.get("last_action", "None")
                
                # Calculate days since deposit
                if last_deposit != "N/A":
                    try:
                        last_date = datetime.datetime.strptime(last_deposit, "%Y-%m-%d").date()
                        days_since = (datetime.date.today() - last_date).days
                    except:
                        days_since = 0
                else:
                    days_since = 0
                
                # Get latest price
                latest_date = max(data.get("tracked_prices", {}).keys()) if data.get("tracked_prices") else "N/A"
                latest_price = data.get("tracked_prices", {}).get(latest_date, 0)
                
                # Get ETF ticker from environment (passed as parameter would be better)
                import os
                etf_ticker = os.getenv("ETF_TICKER", "ETF")
                
                status_emoji = "🟢" if current_status == "active" else "🔴"
                
                response = (
                    f"📊 StockMate Status\n\n"
                    f"Status: {status_emoji} {current_status.upper()}\n"
                    f"ETF: {etf_ticker}\n"
                    f"Latest Price: ${latest_price:.2f} ({latest_date})\n"
                    f"Deposit Amount: ${deposit_amount:,.2f}\n"
                    f"Deposit Date: {last_deposit}\n"
                    f"Days Since Deposit: {days_since}\n"
                    f"Max Wait Period: {wait_period_days} days\n\n"
                    f"Last Action: {last_action}\n\n"
                    f"{'✅ Actively checking for buy signals' if current_status == 'active' else '⏸️ Paused - Use /deposit to resume'}"
                )
                return True, response
            
            # === UNKNOWN COMMAND ===
            else:
                response = (
                    f"❓ Unknown command: {text}\n\n"
                    f"Available commands:\n"
                    f"/deposit <amount>\n"
                    f"/bought\n"
                    f"/status\n"
                    f"/help"
                )
                return True, response
                
        except Exception as e:
            error_msg = f"Error processing command: {str(e)}"
            print(f"❌ {error_msg}")
            return False, f"❌ Error: {str(e)}"

