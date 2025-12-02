import pandas as pd
import numpy as np
import yfinance as yf
import requests
from datetime import datetime, timedelta

# --- DATA PIPELINE (Reused) ---
def fetch_data():
    print("Fetching Data...")
    # 1. Binance USDT (15m)
    base_url = "https://api.binance.com/api/v3/klines"
    end_time = int(datetime.now().timestamp() * 1000)
    all_data = []
    current_end = end_time
    for _ in range(10): 
        params = {"symbol": "USDTTRY", "interval": "15m", "limit": 1000, "endTime": current_end}
        response = requests.get(base_url, params=params)
        data = response.json()
        if not data or isinstance(data, dict): break
        all_data = data + all_data
        current_end = data[0][0] - 1
    usdt = pd.DataFrame(all_data, columns=["OpenTime", "Open", "High", "Low", "Close", "Volume", "CloseTime", "QAV", "Trades", "TBB", "TBQ", "I"])
    usdt["Date"] = pd.to_datetime(usdt["OpenTime"], unit="ms") + pd.Timedelta(hours=3)
    usdt["USDT_Close"] = usdt["Close"].astype(float)
    usdt = usdt.set_index("Date")[["USDT_Close"]]

    # 2. Yahoo USD (Hourly)
    usd = yf.download("TRY=X", period="1y", interval="1h", progress=False)[["Close"]].rename(columns={"Close": "USD_Close"})
    if usd.index.tz is None: usd.index = usd.index.tz_localize("UTC")
    usd.index = usd.index.tz_convert("Etc/GMT-3").tz_localize(None)

    # 3. Yahoo BIST 30 (Daily) for Returns
    bist = yf.download("XU030.IS", period="1y", interval="1d", progress=False)
    bist = bist[["Open", "Close", "High", "Low"]]
    bist.columns = ["BIST_Open", "BIST_Close", "BIST_High", "BIST_Low"]
    
    return usdt, usd, bist

def calculate_signals(usdt, usd, bist):
    # Align & Calc Premium
    start = max(usdt.index.min(), usd.index.min())
    end = min(usdt.index.max(), usd.index.max())
    idx = pd.date_range(start, end, freq="15min")
    df = pd.DataFrame(index=idx).join(usdt)
    df["USD_Close"] = usd.reindex(idx, method='ffill')["USD_Close"].ffill()
    df["Premium"] = (df["USDT_Close"] / df["USD_Close"]) - 1
    
    # Daily Aggregation
    signals = []
    for date in bist.index:
        morning_cutoff = date.replace(hour=9, minute=30)
        night_start = date.replace(hour=0, minute=0)
        mask = (df.index >= night_start) & (df.index <= morning_cutoff)
        night_data = df[mask]
        
        if night_data.empty: continue
        
        avg_prem = night_data["Premium"].mean()
        signals.append({"Date": date, "Avg_Premium": avg_prem})
        
    sig_df = pd.DataFrame(signals).set_index("Date")
    
    # Z-Score
    sig_df["Rolling_Mean"] = sig_df["Avg_Premium"].rolling(20).mean()
    sig_df["Rolling_Std"] = sig_df["Avg_Premium"].rolling(20).std()
    sig_df["Z_Score"] = (sig_df["Avg_Premium"] - sig_df["Rolling_Mean"]) / sig_df["Rolling_Std"]
    
    return sig_df.dropna()

# --- BACKTEST ENGINES ---

def backtest_baseline(signals, bist):
    # Strategy A: Exit at Close (18:05)
    trades = []
    equity = 1.0
    
    for date, row in signals.iterrows():
        if date not in bist.index: continue
        
        z = row["Z_Score"]
        day_data = bist.loc[date]
        ret = (day_data["BIST_Close"] - day_data["BIST_Open"]) / day_data["BIST_Open"]
        
        pnl = 0
        if z > 1.5: # Short
            pnl = -ret
        elif z < -1.5: # Long
            pnl = ret
            
        if pnl != 0:
            equity *= (1 + pnl)
            trades.append(pnl)
            
    return equity, trades

def backtest_time_extension_multi(signals, bist, days_held=1):
    # Generic Time-Based Exit (T+N)
    trades = []
    equity = 1.0
    
    for i in range(len(signals)):
        date = signals.index[i]
        if date not in bist.index: continue
        
        z = signals.iloc[i]["Z_Score"]
        
        try:
            entry_price = bist.loc[date]["BIST_Open"]
            # Find exit day
            current_loc = bist.index.get_loc(date)
            exit_loc = current_loc + days_held
            
            if exit_loc >= len(bist): continue
            
            exit_price = bist.iloc[exit_loc]["BIST_Close"]
            ret = (exit_price - entry_price) / entry_price
            
            pnl = 0
            if z > 1.5: pnl = -ret
            elif z < -1.5: pnl = ret
            
            if pnl != 0:
                equity *= (1 + pnl)
                trades.append(pnl)
        except: continue
            
    return equity, trades

def backtest_buy_and_hold(signals, bist):
    # Benchmark: Buy at first signal date, Hold until last signal date
    if signals.empty: return 1.0, []
    
    start_date = signals.index[0]
    end_date = signals.index[-1]
    
    try:
        start_price = bist.loc[start_date]["BIST_Open"]
        end_price = bist.loc[end_date]["BIST_Close"]
        return end_price / start_price, [] # No trades, just 1 period
    except:
        return 1.0, []

def backtest_adaptive(signals, bist):
    # Strategy C: Trailing Stop Simulation
    # Logic: If trade moves in favor by 1%, set Stop at Entry. 
    # If it moves 2%, set Stop at +1%. 
    # Simplified: If High/Low of day allows for a better exit than Close, take it.
    # We'll simulate a "Perfect Trailing Stop" that captures 50% of the day's range if the trend is correct.
    
    trades = []
    equity = 1.0
    
    for date, row in signals.iterrows():
        if date not in bist.index: continue
        z = row["Z_Score"]
        day = bist.loc[date]
        
        open_p = day["BIST_Open"]
        close_p = day["BIST_Close"]
        high_p = day["BIST_High"]
        low_p = day["BIST_Low"]
        
        pnl = 0
        
        if z > 1.5: # SHORT
            # Best possible for short is Low. Worst is High.
            # Assume we capture 40% of the move from Open to Low if Close < Open (Trend confirmed)
            if close_p < open_p:
                # Trend worked. We trailed and caught some of the drop.
                # Exit = Open - (Open - Low) * 0.6 (Conservative trailing)
                exit_p = open_p - (open_p - low_p) * 0.6
                pnl = (open_p - exit_p) / open_p
            else:
                # Trend failed. We stopped out or closed at loss.
                pnl = (open_p - close_p) / open_p # Standard loss
                
        elif z < -1.5: # LONG
            if close_p > open_p:
                # Trend worked.
                # Exit = Open + (High - Open) * 0.6
                exit_p = open_p + (high_p - open_p) * 0.6
                pnl = (exit_p - open_p) / open_p
            else:
                pnl = (close_p - open_p) / open_p
                
        if pnl != 0:
            equity *= (1 + pnl)
            trades.append(pnl)
            
    return equity, trades

def main():
    print("--- EXIT STRATEGY OPTIMIZATION (EXTENDED) ---")
    usdt, usd, bist = fetch_data()
    signals = calculate_signals(usdt, usd, bist)
    print(f"Signals Generated: {len(signals)} days processed.")
    
    # Run Backtests
    eq_base, tr_base = backtest_baseline(signals, bist)
    eq_t1, tr_t1 = backtest_time_extension_multi(signals, bist, days_held=1)
    eq_t2, tr_t2 = backtest_time_extension_multi(signals, bist, days_held=2)
    eq_t3, tr_t3 = backtest_time_extension_multi(signals, bist, days_held=3)
    eq_adapt, tr_adapt = backtest_adaptive(signals, bist)
    eq_bnh, _ = backtest_buy_and_hold(signals, bist)
    
    # Extended Sweep (T+1 to T+10)
    sweep_results = []
    for day in range(1, 11):
        eq, tr = backtest_time_extension_multi(signals, bist, days_held=day)
        ret = (eq - 1) * 100
        sweep_results.append({"Day": f"T+{day}", "Return": ret, "Trades": len(tr)})
        
    df_sweep = pd.DataFrame(sweep_results)
    print("\n--- SIGNAL DECAY ANALYSIS (T+1 to T+10) ---")
    print(df_sweep.to_string(float_format="%.2f"))
    
    peak = df_sweep.loc[df_sweep["Return"].idxmax()]
    print(f"\nPEAK IMPULSE: {peak['Day']} with {peak['Return']:.2f}% Return")
    
    # Check when it starts to decline
    peak_idx = df_sweep["Return"].idxmax()
    if peak_idx < len(df_sweep) - 1:
        decline_start = df_sweep.iloc[peak_idx+1]
        print(f"DECLINE STARTS: {decline_start['Day']} ({decline_start['Return']:.2f}%)")

if __name__ == "__main__":
    main()
