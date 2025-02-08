import yfinance as yf
import pandas as pd
import datetime
import json
import os
import smtplib
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
DATA_FILE = os.getenv("DATA_FILE")
WAIT_PERIOD_DAYS = int(os.getenv("WAIT_PERIOD_DAYS"))
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


def load_data():
    """Load investment data or initialize new tracking."""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {
        "last_deposit_date": None,
        "deposit_amount": 0.0,
        "brokerage_balance": 0.0,
        "tracked_prices": {},
        "last_action": "None",
    }


def save_data(data):
    """Save investment data to a file."""
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


def get_etf_price(ETF_TICKER):
    """Fetch the latest ETF price."""
    etf = yf.Ticker(ETF_TICKER)
    hist = etf.history(period="1d")
    return round(hist["Close"].iloc[-1], 2) if not hist.empty else None


def days_since_last_deposit(last_deposit_date):
    """Calculate the number of days since the last deposit."""
    if last_deposit_date:
        last_date = datetime.datetime.strptime(last_deposit_date, "%Y-%m-%d").date()
        return (datetime.date.today() - last_date).days
    return None


def analyze_trend(tracked_prices):
    """Analyze the ETF trend based on past price movements."""
    if len(tracked_prices) < 5:
        return None  # Not enough data to analyze trends

    df = pd.DataFrame(tracked_prices, columns=["date", "price"])
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


def should_buy(data, current_price):
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

    return False, f"Price is {current_price}, tracking trend."


def send_notification(subject, message):
    """Send email notification."""
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(
            EMAIL_SENDER, EMAIL_RECEIVER, f"Subject: {subject}\n\n{message}"
        )


def send_telegram_message(message):
    """Send a Telegram message."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    requests.post(url, data=payload)
