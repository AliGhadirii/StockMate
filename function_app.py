import azure.functions as func
from azure.storage.blob import BlobServiceClient
import datetime
import json
import logging
import os

from utils import (
    load_data,
    get_etf_price,
    save_data,
    send_notification,
    send_telegram_message,
    should_buy,
    deposit,
    check_status,
)

app = func.FunctionApp()

# Environment variables
ETF_TICKER = os.getenv("ETF_TICKER")


@app.function_name(name="TimerTrigger")
@app.timer_trigger(
    schedule="0 0 12 * * *", arg_name="myTimer", run_on_startup=False, use_monitor=False
)
def etf_tracker_function(myTimer: func.TimerRequest) -> None:

    if myTimer.past_due:
        logging.info("The timer is past due!")

    data = load_data()
    current_price = get_etf_price(ETF_TICKER)

    if current_price is None:
        logging.error("Error: Could not fetch ETF price.")
        return

    today_str = str(datetime.date.today())
    data["tracked_prices"][today_str] = current_price
    if len(data["tracked_prices"]) > 30:
        oldest_date = min(data["tracked_prices"])
        data["tracked_prices"].pop(oldest_date)

    logging.info(f"Today's {ETF_TICKER} price: {current_price}")
    buy_now, reason = should_buy(data, current_price)
    logging.info(f"[{datetime.date.today()}] {reason}")

    if buy_now:
        logging.info("✅ Action: Buy the ETF today.")
        send_notification("ETF Purchase Alert", reason)
        send_telegram_message(reason)
        data["brokerage_balance"] = 0.0
        data["last_action"] = f"Bought ETF at {current_price}"
        data["tracked_prices"] = []
    else:
        logging.info("⏳ Waiting...")
        data["last_action"] = "Waiting"

    save_data(data)

    logging.info("Python timer trigger function executed.")


@app.function_name(name="HttpTrigger")
@app.route(route="etf_tracker")
@app.http(methods=["GET", "POST"], auth_level=func.AuthLevel.ANONYMOUS)
def http_etf_tracker_function(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Python HTTP trigger function processed a request.")
    deposit_amount = req.params.get("deposit")
    status = req.params.get("status")

    if deposit_amount:
        result = deposit(float(deposit_amount))
        return func.HttpResponse(result, status_code=200)
    elif status:
        data = load_data()
        return func.HttpResponse(json.dumps(data, indent=4), status_code=200)
    else:
        return func.HttpResponse(
            "Invalid request. Provide 'deposit' or 'status' parameter.", status_code=400
        )
