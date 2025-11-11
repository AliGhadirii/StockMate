import json
import os
import datetime
import requests
import yfinance as yf
import pandas as pd
from typing import Dict, Tuple, Optional

# Environment variables (set these in Lambda)
ETF_TICKER = os.getenv("ETF_TICKER")
WAIT_PERIOD_DAYS = int(os.getenv("WAIT_PERIOD_DAYS", "30"))
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Google Drive credentials
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN")
GOOGLE_DRIVE_FILE_ID = os.getenv("GOOGLE_DRIVE_FILE_ID")


class GoogleDriveClient:
    """Client for Google Drive file operations using Google Drive API v3."""
    
    def __init__(self):
        self.client_id = GOOGLE_CLIENT_ID
        self.client_secret = GOOGLE_CLIENT_SECRET
        self.refresh_token = GOOGLE_REFRESH_TOKEN
        self.file_id = GOOGLE_DRIVE_FILE_ID
        self.access_token = None
    
    def get_access_token(self) -> str:
        """Get access token using refresh token."""
        token_url = "https://oauth2.googleapis.com/token"
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        }
        
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        self.access_token = token_data["access_token"]
        return self.access_token
    
    def read_file(self) -> Dict:
        """Read JSON file from Google Drive."""
        try:
            if not self.access_token:
                print("Getting access token...")
                self.get_access_token()
                print("Access token obtained successfully")
            
            # Download file content
            file_url = f"https://www.googleapis.com/drive/v3/files/{self.file_id}?alt=media"
            
            headers = {
                "Authorization": f"Bearer {self.access_token}"
            }
            
            print(f"Attempting to read file from Google Drive (File ID: {self.file_id})")
            response = requests.get(file_url, headers=headers)
            
            print(f"Response status code: {response.status_code}")
            
            if response.status_code == 404:
                # File doesn't exist, return default structure
                print("⚠️ File not found (404). Will create it on first save.")
                return {
                    "last_deposit_date": None,
                    "deposit_amount": 0.0,
                    "brokerage_balance": 0.0,
                    "tracked_prices": {},
                    "last_action": "None",
                }
            
            if response.status_code == 401:
                print("❌ Authentication failed (401). Check your credentials.")
                print(f"Response body: {response.text[:200]}")
                raise Exception("Google Drive authentication failed")
            
            if response.status_code == 403:
                print("❌ Access forbidden (403). Check file permissions.")
                print(f"Response body: {response.text[:200]}")
                raise Exception("Google Drive access forbidden - check file sharing settings")
            
            response.raise_for_status()
            
            # Parse JSON response
            data = response.json()
            print(f"✅ Successfully loaded data from Google Drive")
            print(f"   Last deposit date: {data.get('last_deposit_date')}")
            print(f"   Tracked prices count: {len(data.get('tracked_prices', {}))}")
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error reading from Google Drive: {e}")
            raise
        except Exception as e:
            print(f"❌ Error reading from Google Drive: {e}")
            raise
    
    def write_file(self, data: Dict) -> None:
        """Write JSON file to Google Drive."""
        try:
            if not self.access_token:
                self.get_access_token()
            
            json_content = json.dumps(data, indent=4)
            
            # First, check if file exists
            check_url = f"https://www.googleapis.com/drive/v3/files/{self.file_id}"
            headers = {
                "Authorization": f"Bearer {self.access_token}"
            }
            
            print(f"Checking if file exists (File ID: {self.file_id})...")
            check_response = requests.get(check_url, headers=headers)
            
            if check_response.status_code == 404:
                print("❌ File not found! Please create the file in Google Drive first.")
                print(f"   1. Create a new file in Google Drive")
                print(f"   2. Get its File ID from the URL")
                print(f"   3. Set GOOGLE_DRIVE_FILE_ID environment variable")
                raise Exception("Google Drive file not found - please create it first")
            
            if check_response.status_code == 403:
                print("❌ Access forbidden! Check file permissions.")
                raise Exception("Cannot access Google Drive file - check sharing settings")
            
            check_response.raise_for_status()
            
            # File exists, update it
            print("File exists, updating content...")
            file_url = f"https://www.googleapis.com/upload/drive/v3/files/{self.file_id}?uploadType=media"
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.patch(file_url, headers=headers, data=json_content)
            
            if response.status_code != 200:
                print(f"❌ Update failed with status {response.status_code}")
                print(f"Response: {response.text[:200]}")
            
            response.raise_for_status()
            
            print(f"✅ File updated successfully in Google Drive")
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error writing to Google Drive: {e}")
            raise
        except Exception as e:
            print(f"❌ Error writing to Google Drive: {e}")
            raise


def get_etf_price(etf_ticker: str) -> Optional[float]:
    """
    Fetch the latest ETF price using yfinance with curl_cffi.
    Uses curl_cffi to impersonate a real Chrome browser, bypassing bot detection.
    """
    print(f"Fetching price for {etf_ticker}...")
    
    # Method 1: Try yfinance with curl_cffi session (impersonates Chrome browser)
    try:
        print(f"[Method 1] Trying yfinance with curl_cffi (Chrome impersonation)...")
        
        # Import curl_cffi here to avoid issues if not installed locally
        try:
            from curl_cffi import requests as curl_requests
            
            # Create a session that impersonates Chrome browser
            # This includes realistic TLS fingerprints and headers
            session = curl_requests.Session(impersonate="chrome")
            
            ticker = yf.Ticker(etf_ticker, session=session)
            
            # Try history method first (most reliable)
            hist = ticker.history(period='5d')
            if not hist.empty:
                price = float(hist['Close'].iloc[-1])
                print(f"  ✅ Success! Got price from history: ${price}")
                return round(price, 2)
            
            # Try info method as fallback
            info = ticker.info
            if info and 'currentPrice' in info:
                price = float(info['currentPrice'])
                print(f"  ✅ Success! Got price from ticker.info: ${price}")
                return round(price, 2)
            
            if info and 'regularMarketPrice' in info:
                price = float(info['regularMarketPrice'])
                print(f"  ✅ Success! Got price from regularMarketPrice: ${price}")
                return round(price, 2)
                
        except ImportError:
            print(f"  ⚠️ curl_cffi not installed, falling back to regular requests")
            
            # Fallback to regular requests if curl_cffi not available
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
            })
            
            ticker = yf.Ticker(etf_ticker, session=session)
            hist = ticker.history(period='5d')
            if not hist.empty:
                price = float(hist['Close'].iloc[-1])
                print(f"  ✅ Got price from history: ${price}")
                return round(price, 2)
            
    except Exception as e:
        print(f"  ⚠️ Method 1 failed: {str(e)[:150]}")
    
    # Method 2: Direct Yahoo Finance chart API with curl_cffi
    try:
        print(f"[Method 2] Trying direct Yahoo Finance chart API with curl_cffi...")
        
        try:
            from curl_cffi import requests as curl_requests
            session = curl_requests.Session(impersonate="chrome")
        except ImportError:
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
        
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{etf_ticker}"
        params = {
            'interval': '1d',
            'range': '5d'
        }
        
        response = session.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            chart = data.get('chart', {})
            result = chart.get('result', [])
            
            if result and len(result) > 0:
                meta = result[0].get('meta', {})
                
                # Try regular market price first
                if 'regularMarketPrice' in meta:
                    price = float(meta['regularMarketPrice'])
                    print(f"  ✅ Success! Got price from chart API: ${price}")
                    return round(price, 2)
                
                # Fallback to last closing price from indicators
                indicators = result[0].get('indicators', {})
                quote = indicators.get('quote', [])
                if quote and len(quote) > 0:
                    closes = quote[0].get('close', [])
                    # Get the last non-None close price
                    closes = [c for c in closes if c is not None]
                    if closes:
                        price = float(closes[-1])
                        print(f"  ✅ Success! Got price from chart close data: ${price}")
                        return round(price, 2)
    except Exception as e:
        print(f"  ⚠️ Method 2 failed: {str(e)[:150]}")
    
    # Method 3: Direct Yahoo Finance v10 API with curl_cffi
    try:
        print(f"[Method 3] Trying Yahoo Finance v10 quoteSummary API...")
        
        try:
            from curl_cffi import requests as curl_requests
            session = curl_requests.Session(impersonate="chrome")
        except ImportError:
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
        
        url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{etf_ticker}"
        params = {
            'modules': 'price'
        }
        
        response = session.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            result = data.get('quoteSummary', {}).get('result', [])
            if result and len(result) > 0:
                price_data = result[0].get('price', {})
                if 'regularMarketPrice' in price_data:
                    price = float(price_data['regularMarketPrice'].get('raw', 0))
                    if price > 0:
                        print(f"  ✅ Success! Got price from v10 API: ${price}")
                        return round(price, 2)
    except Exception as e:
        print(f"  ⚠️ Method 3 failed: {str(e)[:150]}")
    
    # All methods failed
    print(f"❌ All methods failed to retrieve price for {etf_ticker}")
    print(f"   Yahoo Finance is blocking all requests from this IP")
    print(f"   Possible solutions:")
    print(f"   - Wait a few hours and try again")
    print(f"   - Use a different API (even paid ones are often < $10/month)")
    print(f"   - Deploy Lambda in a different AWS region")
    return None


def days_since_last_deposit(last_deposit_date: str) -> Optional[int]:
    """Calculate the number of days since the last deposit."""
    if last_deposit_date:
        last_date = datetime.datetime.strptime(last_deposit_date, "%Y-%m-%d").date()
        return (datetime.date.today() - last_date).days
    return None


def analyze_trend(tracked_prices: Dict[str, float]) -> Optional[Dict]:
    """Analyze the ETF trend based on past price movements."""
    if len(tracked_prices) < 5:
        return None  # Not enough data to analyze trends

    df = pd.DataFrame(list(tracked_prices.items()), columns=["date", "price"])
    df["price_change"] = df["price"].pct_change() * 100  # Daily % change

    avg_price = df["price"].mean()
    min_price = df["price"].min()
    max_price = df["price"].max()
    std_dev = df["price"].std()

    return {
        "avg_price": round(avg_price, 2),
        "min_price": round(min_price, 2),
        "max_price": round(max_price, 2),
        "volatility": round(std_dev, 2),
        "latest_price": df["price"].iloc[-1],
    }


def should_buy(data: Dict, current_price: float) -> Tuple[bool, str]:
    """Decide if it's time to buy based on ETF trend and time elapsed."""
    if data["last_deposit_date"] is None:
        return False, "No deposit recorded."

    time_elapsed = days_since_last_deposit(data["last_deposit_date"])
    trend = analyze_trend(data["tracked_prices"])

    if trend is None:
        return False, "Not enough historical data. Waiting."

    dynamic_threshold = trend["avg_price"] * (1 - (trend["volatility"] / 100))

    if current_price <= dynamic_threshold:
        return (
            True,
            f"ETF dropped below dynamic threshold {dynamic_threshold:.2f}. Buy now!",
        )

    if time_elapsed >= WAIT_PERIOD_DAYS:
        return True, f"Max waiting time exceeded ({WAIT_PERIOD_DAYS} days). Buy now!"

    return (
        False,
        f"The current price is {current_price}.\n"
        f"It's above the dynamic threshold {dynamic_threshold:.2f}.\n"
        f"Days since last deposit: {time_elapsed}.\n"
        "Waiting...",
    )


def send_telegram_message(message: str) -> None:
    """Send a Telegram message."""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        response = requests.post(url, data=payload)
        response.raise_for_status()
        print(f"Telegram message sent successfully")
    except Exception as e:
        print(f"Error sending Telegram message: {e}")


def lambda_handler(event, context):
    """
    AWS Lambda handler function.
    This function runs daily to check ETF prices and determine if it's time to buy.
    """
    try:
        print(f"Starting ETF check for {ETF_TICKER} at {datetime.datetime.now()}")
        
        # Initialize Google Drive client
        gdrive = GoogleDriveClient()
        
        # Load data from Google Drive
        print("Loading data from Google Drive...")
        data = gdrive.read_file()
        
        # Get current ETF price
        print(f"Fetching current price for {ETF_TICKER}...")
        current_price = get_etf_price(ETF_TICKER)
        
        if current_price is None:
            error_msg = "Error: Could not fetch ETF price."
            print(error_msg)
            send_telegram_message(f"⚠️ {error_msg}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Could not fetch ETF price'})
            }
        
        # Update today's price
        today_str = str(datetime.date.today())
        data["tracked_prices"][today_str] = current_price
        
        # Keep only last 30 days of prices
        if len(data["tracked_prices"]) > 30:
            oldest_date = min(data["tracked_prices"])
            data["tracked_prices"].pop(oldest_date)
        
        print(f"Today's {ETF_TICKER} price: {current_price}")
        
        # Determine if we should buy
        buy_now, reason = should_buy(data, current_price)
        print(f"[{datetime.date.today()}] {reason}")
        
        # Prepare message with emoji
        if buy_now:
            message = f"✅ BUY SIGNAL\n\n{reason}"
            data["last_action"] = f"Buy signal at {current_price}"
        else:
            message = f"⏳ WAIT\n\n{reason}"
            data["last_action"] = "Waiting"
        
        # Send Telegram notification
        send_telegram_message(message)
        
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
        error_msg = f"Error in lambda_handler: {str(e)}"
        print(error_msg)
        
        # Try to send error notification
        try:
            send_telegram_message(f"❌ Lambda Error: {str(e)}")
        except:
            pass
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


# For local testing
if __name__ == "__main__":
    # Simulate Lambda event and context
    result = lambda_handler({}, None)
    print(json.dumps(result, indent=2))
