import pandas as pd
import numpy as np
import yfinance as yf
import requests
from datetime import datetime, timedelta

def fetch_binance_klines(symbol="USDTTRY", interval="15m", limit=1000):
    """
    Fetches historical klines from Binance.
    Note: Binance public API has limits. We might need to loop for long history.
    For this POC, we'll fetch the max allowed in one go or a reasonable amount.
    """
    base_url = "https://api.binance.com/api/v3/klines"
    # Fetching more data by looping might be needed for a full year, 
    # but let's start with the last ~10 days (1000 * 15m = 250 hours = ~10 days)
    # Actually, let's try to get more. 
    
    end_time = int(datetime.now().timestamp() * 1000)
    all_data = []
    
    # Fetch last ~90 days in chunks
    # 15m candles per day = 96. 90 days = 8640 candles.
    # Binance limit is 1000. We need ~9 loops.
    
    current_end = end_time
    for _ in range(10): 
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": 1000,
            "endTime": current_end
        }
        response = requests.get(base_url, params=params)
        data = response.json()
        
        if not data or isinstance(data, dict): # Error or empty
            break
            
        all_data = data + all_data # Prepend to keep order
        current_end = data[0][0] - 1 # Move back in time
        
    df = pd.DataFrame(all_data, columns=[
        "OpenTime", "Open", "High", "Low", "Close", "Volume", 
        "CloseTime", "QuoteAssetVolume", "Trades", "TakerBuyBase", "TakerBuyQuote", "Ignore"
    ])
    
    df["Date"] = pd.to_datetime(df["OpenTime"], unit="ms")
    df["USDT_Close"] = df["Close"].astype(float)
    df = df[["Date", "USDT_Close"]]
    
    # Adjust to Turkey Time (UTC+3)
    # Binance returns UTC.
    df["Date"] = df["Date"] + pd.Timedelta(hours=3)
    
    return df.set_index("Date")

def fetch_yahoo_data():
    # USD/TRY
    print("Fetching USD/TRY from Yahoo...")
    usd_try = yf.download("TRY=X", period="1y", interval="1h", progress=False)
    usd_try = usd_try[["Close"]].rename(columns={"Close": "USD_Close"})
    # Yahoo is usually UTC or local exchange time. Forex is 24/5 roughly.
    # Let's assume UTC for alignment and shift if needed. 
    # Actually yfinance returns timezone-aware usually.
    if usd_try.index.tz is None:
        usd_try.index = usd_try.index.tz_localize("UTC")
    usd_try.index = usd_try.index.tz_convert("Etc/GMT-3") # Turkey Time
    usd_try.index = usd_try.index.tz_localize(None) # Remove tz info for easy merging

    # BIST 30 (XU030.IS)
    print("Fetching BIST 30 from Yahoo...")
    bist30 = yf.download("XU030.IS", period="1y", interval="1d", progress=False)
    bist30 = bist30[["Open", "Close", "Low", "High"]]
    bist30.columns = ["BIST_Open", "BIST_Close", "BIST_Low", "BIST_High"]
    # BIST data is daily.
    
    return usd_try, bist30

def align_and_calculate_premium(usdt_df, usd_df):
    # Resample USDT to hourly to match USD (or keep 15m and ffill USD)
    # User requested 15m analysis. So we keep 15m.
    
    # Create a common 15m index covering the range
    start_date = max(usdt_df.index.min(), usd_df.index.min())
    end_date = min(usdt_df.index.max(), usd_df.index.max())
    
    full_idx = pd.date_range(start=start_date, end=end_date, freq="15min")
    df = pd.DataFrame(index=full_idx)
    
    # Merge USDT (Exact matches)
    df = df.join(usdt_df)
    
    # Merge USD (Forward Fill)
    # First reindex USD to 15m
    usd_resampled = usd_df.reindex(full_idx, method='ffill')
    df["USD_Close"] = usd_resampled["USD_Close"]
    
    # Forward fill USD for weekends/nights
    df["USD_Close"] = df["USD_Close"].ffill()
    
    # Calculate Premium
    df["Premium"] = (df["USDT_Close"] / df["USD_Close"]) - 1
    
    return df

def analyze_nightly_fear(premium_df, bist_df):
    results = []
    
    # Iterate over each trading day in BIST
    for date in bist_df.index:
        # Define "Night" window: Previous day 18:00 to Current day 09:30
        # Or specifically 00:00 to 09:30 as requested.
        
        morning_cutoff = date.replace(hour=9, minute=30, second=0)
        night_start = date.replace(hour=0, minute=0, second=0)
        
        # Filter premium data for this window
        night_data = premium_df[(premium_df.index >= night_start) & (premium_df.index <= morning_cutoff)]
        
        if night_data.empty:
            continue
            
        avg_premium = night_data["Premium"].mean()
        max_premium = night_data["Premium"].max()
        vol_premium = night_data["Premium"].std()
        
        # Calculate BIST Gap
        # Gap = Today Open - Yesterday Close
        # We need yesterday's close.
        prev_idx = bist_df.index.get_loc(date) - 1
        if prev_idx < 0:
            continue
            
        prev_close = bist_df.iloc[prev_idx]["BIST_Close"]
        today_open = bist_df.loc[date]["BIST_Open"]
        
        gap_pct = (today_open - prev_close) / prev_close
        
        results.append({
            "Date": date.date(),
            "Avg_Night_Premium": avg_premium,
            "Max_Night_Premium": max_premium,
            "Premium_Vol": vol_premium,
            "BIST_Gap": gap_pct
        })
        
    return pd.DataFrame(results)

def main():
    print("--- MIDNIGHT EXPRESS: FEAR GAUGE ---")
    
    # 1. Fetch Data
    usdt_df = fetch_binance_klines()
    usd_df, bist_df = fetch_yahoo_data()
    
    print(f"USDT Data: {len(usdt_df)} rows")
    print(f"USD Data: {len(usd_df)} rows")
    print(f"BIST Data: {len(bist_df)} rows")
    
    # 2. Align & Calc Premium
    print("Aligning data and calculating premium...")
    premium_df = align_and_calculate_premium(usdt_df, usd_df)
    
    # 3. Analyze Nightly Fear vs Gap
    print("Analyzing nightly patterns...")
    analysis_df = analyze_nightly_fear(premium_df, bist_df)
    
    if analysis_df.empty:
        print("No analysis generated. Check data alignment.")
        return

    # 4. Results
    print("\n--- CORRELATION ANALYSIS ---")
    corr = analysis_df["Avg_Night_Premium"].corr(analysis_df["BIST_Gap"])
    print(f"Correlation (Night Premium vs Gap): {corr:.4f}")
    
    print("\n--- CONDITIONAL PROBABILITY ---")
    # Thresholds
    thresholds = [0.005, 0.01, 0.02] # 0.5%, 1%, 2%
    
    for t in thresholds:
        high_fear = analysis_df[analysis_df["Avg_Night_Premium"] > t]
        if high_fear.empty:
            print(f"No days with Premium > {t*100}%")
            continue
            
        negative_gaps = high_fear[high_fear["BIST_Gap"] < 0]
        prob = len(negative_gaps) / len(high_fear)
        avg_gap = high_fear["BIST_Gap"].mean()
        
        print(f"Threshold > {t*100}% Premium:")
        print(f"  - Occurrences: {len(high_fear)}")
        print(f"  - Probability of Negative Gap: {prob*100:.1f}%")
        print(f"  - Average Gap Size: {avg_gap*100:.2f}%")
        
    # Save results
    analysis_df.to_csv("research/midnight_express_results.csv", index=False)
    print("\nResults saved to research/midnight_express_results.csv")

if __name__ == "__main__":
    main()
