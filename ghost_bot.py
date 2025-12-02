import os
import sys
import pandas as pd
import requests
from pytrends.request import TrendReq


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

def main():
    print("--- GHOST BOT: STARTED ---")
    
    # 1. Fetch Data (Last 90 Days)
    try:
        print("Fetching Google Trends data...")
        
        # Configure retries for 429 errors
        session = requests.Session()
        retries = requests.adapters.Retry(
            total=5,
            backoff_factor=1, # 1s, 2s, 4s, 8s, 16s
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        session.mount("https://", requests.adapters.HTTPAdapter(max_retries=retries))
        
        pytrends = TrendReq(hl='tr-TR', tz=180, requests_args={'verify': True}, timeout=(10,25))
        # Monkey patch the session used by pytrends if possible, or just rely on internal retries if they exist.
        # Actually TrendReq uses requests.get/post internally. 
        # Better approach: TrendReq accepts 'requests_args' but not a session directly in all versions.
        # However, we can try to be robust.
        
        # Let's implement a manual retry loop for the high level action
        max_retries = 3
        df = pd.DataFrame()
        
        for attempt in range(max_retries):
            try:
                kw_list = ["Halka Arz"]
                pytrends.build_payload(kw_list, cat=0, timeframe='today 3-m', geo='TR', gprop='')
                df = pytrends.interest_over_time()
                if not df.empty:
                    break
            except Exception as e:
                print(f"Attempt {attempt+1} failed: {e}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2 ** (attempt + 1)) # Exponential backoff
                else:
                    raise e

        if df.empty:
            print("No data found.")
            return
            
        print(f"Data fetched: {len(df)} rows.")
        
    except Exception as e:
        print(f"Error fetching data: {e}")
        # Fallback or exit? For a bot, we might want to retry or just log.
        sys.exit(1)

    # 2. Calculate Z-Score
    # We use a 30-day rolling window as defined in Phase 4
    window = 30
    col = "Halka Arz"
    
    # Ensure we have enough data
    if len(df) < window:
        print("Not enough data for rolling window.")
        return

    rolling_mean = df[col].rolling(window=window).mean()
    rolling_std = df[col].rolling(window=window).std()
    
    # Calculate latest Z-Score
    latest_val = df[col].iloc[-1]
    latest_mean = rolling_mean.iloc[-1]
    latest_std = rolling_std.iloc[-1]
    
    if latest_std == 0:
        z_score = 0
    else:
        z_score = (latest_val - latest_mean) / latest_std
        
    print(f"Latest Value: {latest_val}")
    print(f"Rolling Mean (30d): {latest_mean:.2f}")
    print(f"Z-Score: {z_score:.2f}")
    
    # 3. Decision Logic
    THRESHOLD = 1.5
    
    if z_score > THRESHOLD:
        message = f"""
*👻 GHOST BOT REPORT*
----------------
*Sinyal:* MOMENTUM LONG (Halka Arz İlgisi)

*Z-Score:* {z_score:.2f} (Eşik: {THRESHOLD})
*Güncel Değer:* {latest_val}

*ACTION:*
-> BUY BIST 30
-> HOLD: 3 Gün

_Bu otomatik bir mesajdır._
        """
        
        print("Signal Detected! Sending Telegram Alert...")
        send_telegram_alert(message)
    else:
        print("No Signal. Z-Score is below threshold.")

if __name__ == "__main__":
    main()
