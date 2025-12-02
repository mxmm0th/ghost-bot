import pandas as pd
import numpy as np
import yfinance as yf
import requests
from datetime import datetime, timedelta
from itertools import product

# --- DATA PIPELINE (Reused from Phase 6) ---
def fetch_binance_klines(symbol="USDTTRY", interval="15m"):
    base_url = "https://api.binance.com/api/v3/klines"
    end_time = int(datetime.now().timestamp() * 1000)
    all_data = []
    current_end = end_time
    
    # Fetch last ~90 days
    for _ in range(10): 
        params = {"symbol": symbol, "interval": interval, "limit": 1000, "endTime": current_end}
        response = requests.get(base_url, params=params)
        data = response.json()
        if not data or isinstance(data, dict): break
        all_data = data + all_data
        current_end = data[0][0] - 1
        
    df = pd.DataFrame(all_data, columns=["OpenTime", "Open", "High", "Low", "Close", "Volume", "CloseTime", "QAV", "Trades", "TBB", "TBQ", "I"])
    df["Date"] = pd.to_datetime(df["OpenTime"], unit="ms") + pd.Timedelta(hours=3) # TRT
    df["USDT_Close"] = df["Close"].astype(float)
    return df.set_index("Date")[["USDT_Close"]]

def fetch_yahoo_data():
    usd_try = yf.download("TRY=X", period="1y", interval="1h", progress=False)
    usd_try = usd_try[["Close"]].rename(columns={"Close": "USD_Close"})
    if usd_try.index.tz is None: usd_try.index = usd_try.index.tz_localize("UTC")
    usd_try.index = usd_try.index.tz_convert("Etc/GMT-3").tz_localize(None)

    bist30 = yf.download("XU030.IS", period="1y", interval="1d", progress=False)
    bist30 = bist30[["Open", "Close"]]
    bist30.columns = ["BIST_Open", "BIST_Close"]
    return usd_try, bist30

def prepare_data():
    print("Fetching Data...")
    usdt = fetch_binance_klines()
    usd, bist = fetch_yahoo_data()
    
    # Align
    start = max(usdt.index.min(), usd.index.min())
    end = min(usdt.index.max(), usd.index.max())
    idx = pd.date_range(start, end, freq="15min")
    
    df = pd.DataFrame(index=idx)
    df = df.join(usdt)
    df["USD_Close"] = usd.reindex(idx, method='ffill')["USD_Close"].ffill()
    df["Premium"] = (df["USDT_Close"] / df["USD_Close"]) - 1
    
    # Nightly Aggregation
    nightly_stats = []
    for date in bist.index:
        morning_cutoff = date.replace(hour=9, minute=30)
        night_start = date.replace(hour=0, minute=0)
        
        mask = (df.index >= night_start) & (df.index <= morning_cutoff)
        night_data = df[mask]
        
        if night_data.empty: continue
        
        avg_prem = night_data["Premium"].mean()
        
        # Get Day's Return (Open to Close - Scalping)
        # Strategy: Enter Open, Exit Close
        day_open = bist.loc[date]["BIST_Open"]
        day_close = bist.loc[date]["BIST_Close"]
        day_return = (day_close - day_open) / day_open
        
        nightly_stats.append({
            "Date": date,
            "Avg_Premium": avg_prem,
            "Day_Return": day_return
        })
        
    return pd.DataFrame(nightly_stats).set_index("Date")

# --- STRATEGY ENGINE ---
def backtest(df, z_window, z_threshold_long, z_threshold_short):
    # Calculate Rolling Z-Score of Premium
    # We want to know if LAST NIGHT's premium was anomalous relative to recent history
    
    df["Rolling_Mean"] = df["Avg_Premium"].rolling(window=z_window).mean()
    df["Rolling_Std"] = df["Avg_Premium"].rolling(window=z_window).std()
    df["Z_Score"] = (df["Avg_Premium"] - df["Rolling_Mean"]) / df["Rolling_Std"]
    
    # Shift Z-Score? No, Avg_Premium is for the night BEFORE the trading day.
    # So Z-Score calculated on row T is available for trading on day T.
    # Wait, rolling calculation includes current row. That's correct.
    
    trades = []
    equity = 1.0
    
    for date, row in df.iterrows():
        z = row["Z_Score"]
        ret = row["Day_Return"]
        
        if pd.isna(z): continue
        
        action = None
        pnl = 0
        
        # LOGIC:
        # High Premium (Fear) -> Short
        # Low Premium (Relief) -> Long
        
        if z > z_threshold_short:
            action = "SHORT"
            pnl = -ret # Short Return
        elif z < -z_threshold_long:
            action = "LONG"
            pnl = ret # Long Return
            
        if action:
            equity *= (1 + pnl)
            trades.append({
                "Date": date,
                "Action": action,
                "Z": z,
                "Return": pnl,
                "Equity": equity
            })
            
    return trades

def optimize():
    df = prepare_data()
    print(f"Data Prepared: {len(df)} days")
    
    # Grid Search
    windows = [5, 10, 20] # Short-term memory for Z-score
    thresholds = [1.0, 1.5, 2.0] # Sensitivity
    
    best_score = -999
    best_params = None
    best_trades = []
    
    print("Optimizing...")
    for w, t_long, t_short in product(windows, thresholds, thresholds):
        trades = backtest(df.copy(), w, t_long, t_short)
        if not trades: continue
        
        final_equity = trades[-1]["Equity"]
        total_return = final_equity - 1
        trade_count = len(trades)
        
        # Score: Return * log(Trades) (Reward activity but prioritize profit)
        if trade_count < 5: continue # Too few trades
        
        score = total_return
        
        if score > best_score:
            best_score = score
            best_params = (w, t_long, t_short)
            best_trades = trades
            
    print("\n--- OPTIMIZATION RESULTS ---")
    print(f"Best Params: Window={best_params[0]}, Long_Thresh={best_params[1]}, Short_Thresh={best_params[2]}")
    print(f"Total Return: {best_score*100:.2f}%")
    print(f"Trade Count: {len(best_trades)}")
    
    # Show last 5 trades
    print("\nLast 5 Trades:")
    print(pd.DataFrame(best_trades).tail(5))

if __name__ == "__main__":
    optimize()
