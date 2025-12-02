import os
import sys
import pandas as pd
import numpy as np
import requests
import yfinance as yf
from datetime import datetime, timedelta

# --- CONFIGURATION ---
Z_WINDOW = 20
Z_THRESHOLD = 0.5 # Lowered for agility (Grey Swan)

def send_telegram_alert(message):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("Error: Telegram credentials not found in environment variables.")
        return
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("Telegram alert sent successfully.")
        else:
            print(f"Error sending Telegram alert: {response.text}")
    except Exception as e:
        print(f"Error sending Telegram alert: {e}")

def fetch_binance_klines(days=40):
    """
    Fetches historical klines from Binance for USDT/TRY.
    """
    symbol = "USDTTRY"
    interval = "15m"
    base_url = "https://api.binance.com/api/v3/klines"
    
    end_time = int(datetime.now().timestamp() * 1000)
    all_data = []
    
    # Estimate loops needed: 96 candles/day * days / 1000 limit
    loops = int((days * 96) / 1000) + 2
    
    current_end = end_time
    for _ in range(loops): 
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": 1000,
            "endTime": current_end
        }
        try:
            response = requests.get(base_url, params=params, timeout=10)
            data = response.json()
            
            if not data or isinstance(data, dict) and "code" in data: # Error or empty
                break
                
            all_data = data + all_data # Prepend to keep order
            current_end = data[0][0] - 1 # Move back in time
            
            # Stop if we have enough data
            if len(all_data) > days * 96:
                break
        except Exception as e:
            print(f"Error fetching Binance data: {e}")
            break
        
    if not all_data:
        return pd.DataFrame()

    df = pd.DataFrame(all_data, columns=[
        "OpenTime", "Open", "High", "Low", "Close", "Volume", 
        "CloseTime", "QuoteAssetVolume", "Trades", "TakerBuyBase", "TakerBuyQuote", "Ignore"
    ])
    
    df["Date"] = pd.to_datetime(df["OpenTime"], unit="ms")
    df["USDT_Close"] = df["Close"].astype(float)
    df = df[["Date", "USDT_Close"]]
    
    # Adjust to Turkey Time (UTC+3)
    df["Date"] = df["Date"] + pd.Timedelta(hours=3)
    
    return df.set_index("Date")

def fetch_yahoo_usd(days=40):
    """
    Fetches USD/TRY data from Yahoo Finance.
    """
    print("Fetching USD/TRY from Yahoo...")
    try:
        # Fetch a bit more to be safe
        period = f"{days+5}d"
        # Yahoo interval 1h is good for alignment with 15m
        usd_try = yf.download("TRY=X", period=period, interval="1h", progress=False)
        
        if usd_try.empty:
            return pd.DataFrame()
            
        usd_try = usd_try[["Close"]].rename(columns={"Close": "USD_Close"})
        
        # Timezone handling
        if usd_try.index.tz is None:
            usd_try.index = usd_try.index.tz_localize("UTC")
        
        # Convert to Turkey Time (Etc/GMT-3 is UTC+3)
        usd_try.index = usd_try.index.tz_convert("Etc/GMT-3") 
        usd_try.index = usd_try.index.tz_localize(None) # Remove tz info for easy merging
        
        return usd_try
    except Exception as e:
        print(f"Error fetching Yahoo data: {e}")
        return pd.DataFrame()

def calculate_nightly_premium_history(usdt_df, usd_df):
    """
    Calculates the nightly premium history.
    """
    if usdt_df.empty or usd_df.empty:
        return pd.Series()

    # Create a common 15m index covering the range
    start_date = max(usdt_df.index.min(), usd_df.index.min())
    end_date = min(usdt_df.index.max(), usd_df.index.max())
    
    full_idx = pd.date_range(start=start_date, end=end_date, freq="15min")
    df = pd.DataFrame(index=full_idx)
    
    # Merge USDT (Exact matches)
    df = df.join(usdt_df)
    
    # Merge USD (Forward Fill)
    usd_resampled = usd_df.reindex(full_idx, method='ffill')
    df["USD_Close"] = usd_resampled["USD_Close"]
    
    # Forward fill USD for weekends/nights
    df["USD_Close"] = df["USD_Close"].ffill()
    
    # Calculate Premium
    df["Premium"] = (df["USDT_Close"] / df["USD_Close"]) - 1
    
    # Aggregate to Daily "Nightly Premium"
    # We want to average the premium during the night (e.g., 18:00 to 09:30 next day)
    # For simplicity in this bot, let's take the daily average of the premium 
    # OR follow the research logic: 18:00 previous day to 09:30 current day.
    
    # Let's simplify for the bot: Average Premium of the "Morning" (00:00 to 09:30)
    # This represents the overnight sentiment leading into the open.
    
    # Resample to daily, taking the mean of hours 00:00-09:30
    
    # Filter for hours 0-9
    morning_df = df[df.index.hour < 10]
    
    daily_prem = morning_df["Premium"].resample("D").mean()
    
    return daily_prem.dropna()


def main():
    print("--- MIDNIGHT HUNTER: STARTED ---")
    
    # 1. Fetch Data
    print("Fetching data...")
    usdt = fetch_binance_klines(days=40) 
    usd = fetch_yahoo_usd(days=40)
    
    # 2. Calculate History
    print("Calculating premiums...")
    daily_prem = calculate_nightly_premium_history(usdt, usd)
    
    if len(daily_prem) < Z_WINDOW:
        print(f"Not enough data. Need {Z_WINDOW} days, got {len(daily_prem)}.")
        return

    # 3. Calculate Z-Score
    rolling_mean = daily_prem.rolling(window=Z_WINDOW).mean()
    rolling_std = daily_prem.rolling(window=Z_WINDOW).std()
    
    today = datetime.now().date()
    # Check if we have data for 'today' (morning)
    if today not in daily_prem.index:
        print(f"No data for today ({today}). Market might not be open or data delayed.")
        # Fallback to last available day for testing/demo
        latest_date = daily_prem.index[-1]
        print(f"Using last available date: {latest_date}")
        current_prem = daily_prem.iloc[-1]
        current_mean = rolling_mean.iloc[-1]
        current_std = rolling_std.iloc[-1]
    else:
        current_prem = daily_prem.loc[today]
        current_mean = rolling_mean.loc[today]
        current_std = rolling_std.loc[today]
        
    z_score = (current_prem - current_mean) / current_std
    
    print(f"Date: {today}")
    print(f"Nightly Premium: {current_prem*100:.4f}%")
    print(f"Rolling Mean (20d): {current_mean*100:.4f}%")
    print(f"Z-Score: {z_score:.2f}")
    
    # 4. Decision (T+1 Strategy)
    action = "WAIT"
    reason = "Z-Score within normal range"
    
    if z_score > Z_THRESHOLD:
        action = "SHORT"
        reason = f"Fear Spike (Z > {Z_THRESHOLD})"
    elif z_score < -Z_THRESHOLD:
        action = "LONG"
        reason = f"Relief Dip (Z < -{Z_THRESHOLD})"
        
    print(f"DECISION: {action} ({reason})")
    
    # 5. Alert
    if action != "WAIT":
        message = f"""
*🦅 MIDNIGHT HUNTER: {action} SIGNAL (T+1)*
----------------------
*Date:* {today}
*Action:* {action}
*Reason:* {reason}

*Stats:*
- Premium: {current_prem*100:.4f}%
- Z-Score: {z_score:.2f}

*STRATEGY (T+1):*
1. ENTER: Market Open (09:55) Today.
2. HOLD: Overnight.
3. EXIT: Market Close (18:05) TOMORROW.
4. STOP LOSS: Move to Breakeven at 18:00 Today.

_Good hunting._
        """
        send_telegram_alert(message)
    else:
        print("No signal generated.")

if __name__ == "__main__":
    main()
