import datetime
import schedule
import time

from utils import (
    load_data,
    get_etf_price,
    save_data,
    send_notification,
    send_telegram_message,
    should_buy,
)


def main():
    data = load_data()
    current_price = get_etf_price()

    if current_price is None:
        print("Error: Could not fetch ETF price.")
        return

    data["tracked_prices"].append([str(datetime.date.today()), current_price])
    if len(data["tracked_prices"]) > 30:
        data["tracked_prices"].pop(0)

    buy_now, reason = should_buy(data, current_price)
    print(f"[{datetime.date.today()}] {reason}")

    if buy_now:
        print("✅ Action: Buy the ETF today.")
        send_notification("ETF Purchase Alert", reason)
        send_telegram_message(reason)
        data["brokerage_balance"] = 0.0
        data["last_action"] = f"Bought ETF at {current_price}"
        data["tracked_prices"] = []
    else:
        print("⏳ Waiting...")
        data["last_action"] = "Waiting"

    save_data(data)


# ------------------------- AUTOMATIC SCHEDULING -------------------------

schedule.every().day.at("12:00").do(main)

while True:
    schedule.run_pending()
    time.sleep(60)  # Check every minute
