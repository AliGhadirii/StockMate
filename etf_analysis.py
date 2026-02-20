"""
ETF Analysis Module for StockMate
Handles ETF price fetching, trend analysis, and buy signal generation.
"""

import datetime
import requests
import yfinance as yf
import pandas as pd
from typing import Dict, Tuple, Optional


def get_etf_price(etf_ticker: str) -> Optional[float]:
    """
    Fetch the latest ETF price using yfinance with curl_cffi.
    Uses curl_cffi to impersonate a real Chrome browser, bypassing bot detection.
    
    Args:
        etf_ticker: ETF symbol (e.g., 'VOO', 'IVV.AX')
        
    Returns:
        Current ETF price or None if fetch fails
    """
    print(f"Fetching price for {etf_ticker}...")
    
    # Method 1: Try yfinance with curl_cffi session (impersonates Chrome browser)
    try:
        print(f"[Method 1] Trying yfinance with curl_cffi (Chrome impersonation)...")
        
        try:
            from curl_cffi import requests as curl_requests
            
            # Create a session that impersonates Chrome browser
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
    """Calculate the number of days since the last deposit.
    
    Args:
        last_deposit_date: Date string in format 'YYYY-MM-DD'
        
    Returns:
        Number of days or None if date is invalid
    """
    if last_deposit_date:
        last_date = datetime.datetime.strptime(last_deposit_date, "%Y-%m-%d").date()
        return (datetime.date.today() - last_date).days
    return None


def analyze_trend(tracked_prices: Dict[str, float]) -> Optional[Dict]:
    """Analyze the ETF trend based on past price movements.
    
    Args:
        tracked_prices: Dictionary of date -> price
        
    Returns:
        Dictionary containing trend analysis or None if insufficient data
    """
    if len(tracked_prices) < 5:
        return None  # Not enough data to analyze trends

    df = pd.DataFrame(list(tracked_prices.items()), columns=["date", "price"])
    df = df.sort_values("date")  # Ensure chronological order
    df["price_change"] = df["price"].pct_change() * 100  # Daily % change

    current_price = df["price"].iloc[-1]
    avg_price = df["price"].mean()
    min_price = df["price"].min()
    max_price = df["price"].max()
    std_dev = df["price"].std()
    
    # Calculate volatility as percentage (FIXED BUG)
    volatility_pct = (std_dev / avg_price) * 100 if avg_price > 0 else 0
    
    # Detect trend direction: compare recent vs older prices
    if len(df) >= 10:
        recent_avg = df["price"].tail(5).mean()  # Last 5 days
        older_avg = df["price"].iloc[-10:-5].mean()  # Days 6-10 ago
        trend_direction = "uptrend" if recent_avg > older_avg else "downtrend"
        trend_strength_pct = abs((recent_avg - older_avg) / older_avg) * 100
    else:
        trend_direction = "neutral"
        trend_strength_pct = 0
    
    # Price position: where is current price in the 30-day range?
    price_range = max_price - min_price
    if price_range > 0:
        price_percentile = ((current_price - min_price) / price_range) * 100
    else:
        price_percentile = 50

    return {
        "avg_price": round(avg_price, 2),
        "min_price": round(min_price, 2),
        "max_price": round(max_price, 2),
        "std_dev": round(std_dev, 2),
        "volatility_pct": round(volatility_pct, 2),
        "latest_price": round(current_price, 2),
        "trend_direction": trend_direction,
        "trend_strength_pct": round(trend_strength_pct, 2),
        "price_percentile": round(price_percentile, 1),
    }


def backfill_price_history(etf_ticker: str, tracked_prices: Dict[str, float], days: int = 30) -> Dict[str, float]:
    """Fetch historical closing prices to fill gaps left when the lambda was offline.

    Only fills dates that are not already present in tracked_prices, so existing
    manually-tracked entries are never overwritten.

    Args:
        etf_ticker: ETF symbol (e.g. 'VOO', 'IVV.AX')
        tracked_prices: Existing date->price dictionary (mutated in-place and returned)
        days: How many calendar days of history to request from yfinance

    Returns:
        Updated tracked_prices dictionary
    """
    try:
        print(f"Backfilling historical prices for {etf_ticker} (last {days} days)...")

        try:
            from curl_cffi import requests as curl_requests
            session = curl_requests.Session(impersonate="chrome")
        except ImportError:
            session = requests.Session()
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })

        ticker = yf.Ticker(etf_ticker, session=session)
        hist = ticker.history(period=f"{days}d")

        if hist.empty:
            print("  ⚠️ Backfill: no historical data returned by yfinance")
            return tracked_prices

        filled = 0
        for ts, row in hist.iterrows():
            date_str = str(ts.date())
            if date_str not in tracked_prices:
                tracked_prices[date_str] = round(float(row["Close"]), 2)
                filled += 1

        print(f"  ✅ Backfilled {filled} missing price entries")
    except Exception as e:
        print(f"  ⚠️ Backfill failed: {str(e)[:150]}")

    return tracked_prices


def should_buy(data: Dict, current_price: float, wait_period_days: int) -> Tuple[bool, str]:
    """Decide if it's time to buy based on ETF trend and time elapsed.
    
    Strategy for monthly S&P 500 investing:
    - Target: Invest around 2/3 of WAIT_PERIOD_DAYS
    - Maximum wait: WAIT_PERIOD_DAYS (hard limit)
    - Opportunistic: Buy earlier if significant dip occurs
    
    Args:
        data: Dictionary containing investment data
        current_price: Current ETF price
        wait_period_days: Maximum number of days to wait
        
    Returns:
        Tuple of (should_buy: bool, reason: str)
    """
    if data["last_deposit_date"] is None:
        return False, "No deposit recorded."

    time_elapsed = days_since_last_deposit(data["last_deposit_date"])
    trend = analyze_trend(data["tracked_prices"])

    if trend is None:
        return False, "Not enough historical data. Waiting."

    # Calculate time thresholds based on WAIT_PERIOD_DAYS
    early_buy_threshold = int(wait_period_days * 0.67)  # ~2/3 of wait period
    standard_schedule = int(wait_period_days * 0.85)  # ~85% of wait period
    max_wait = wait_period_days  # Hard limit from environment variable

    # Fixed volatility calculation - use percentage not absolute dollars
    strong_dip_threshold = trend["avg_price"] * (1 - trend["volatility_pct"] / 100)
    moderate_dip_threshold = trend["avg_price"] * (1 - trend["volatility_pct"] / 200)  # Half volatility
    
    # === BUY SIGNALS ===
    
    # SIGNAL 1: Strong dip (1+ std dev below average) - buy immediately
    if current_price <= strong_dip_threshold:
        return (
            True,
            f"🎯 Strong Dip Detected!\n"
            f"Current: ${current_price:.2f}\n"
            f"Strong dip threshold: ${strong_dip_threshold:.2f}\n"
            f"Price at {trend['price_percentile']:.0f}th percentile of 30-day range\n"
            f"Days since deposit: {time_elapsed}\n"
            f"Action: Buying the dip!",
        )
    
    # SIGNAL 2: Moderate dip + nearing schedule
    if time_elapsed >= early_buy_threshold and current_price <= moderate_dip_threshold:
        return (
            True,
            f"✅ Good Buy Opportunity\n"
            f"Current: ${current_price:.2f}\n"
            f"Moderate dip threshold: ${moderate_dip_threshold:.2f}\n"
            f"Days since deposit: {time_elapsed}\n"
            f"Action: Buying below average near scheduled time",
        )
    
    # SIGNAL 3: Standard schedule - but avoid peaks
    if time_elapsed >= standard_schedule:
        # Safety check: if price is at 30-day high, wait until max_wait
        if trend["price_percentile"] >= 85 and time_elapsed < max_wait:
            return (
                False,
                f"⏳ Schedule Reached BUT Price Near Peak\n"
                f"Current: ${current_price:.2f} (at {trend['price_percentile']:.0f}th percentile)\n"
                f"30-day average: ${trend['avg_price']:.2f}\n"
                f"Days since deposit: {time_elapsed}\n"
                f"Suggestion: Waiting for pullback (will buy by day {max_wait})",
            )
        else:
            # Price is reasonable OR max wait reached
            return (
                True,
                f"✅ Investment Schedule\n"
                f"Current: ${current_price:.2f}\n"
                f"30-day average: ${trend['avg_price']:.2f}\n"
                f"Price position: {trend['price_percentile']:.0f}th percentile\n"
                f"Days since deposit: {time_elapsed}\n"
                f"Action: {'Maintaining regular schedule' if trend['price_percentile'] < 85 else 'Maximum wait reached'}",
            )
    
    # === NO BUY SIGNAL ===
    return (
        False,
        f"⏳ Waiting for Better Entry\n"
        f"Current: ${current_price:.2f}\n"
        f"30-day average: ${trend['avg_price']:.2f}\n"
        f"Strong dip target: ${strong_dip_threshold:.2f}\n"
        f"Trend: {trend['trend_direction']} ({trend['trend_strength_pct']:.1f}%)\n"
        f"Price position: {trend['price_percentile']:.0f}th percentile\n"
        f"Days since deposit: {time_elapsed}/{max_wait}\n"
        f"Strategy: Will buy by day {standard_schedule} (or day {max_wait} if price at peak)",
    )

