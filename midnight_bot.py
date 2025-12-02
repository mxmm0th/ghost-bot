import os
import sys
import pandas as pd
import numpy as np
import requests
import yfinance as yf
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURATION ---
Z_WINDOW = 20
Z_THRESHOLD = 0.5 # Lowered for agility (Grey Swan)
EMAIL_RECEIVER = "vojerkan@gmail.com"

# ... (Email and Fetch functions remain the same) ...

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
        subject = f"🦅 MIDNIGHT HUNTER: {action} SIGNAL (T+1)"
        body = f"""
        MIDNIGHT HUNTER REPORT
        ----------------------
        Date: {today}
        Action: {action}
        Reason: {reason}
        
        Stats:
        - Premium: {current_prem*100:.4f}%
        - Z-Score: {z_score:.2f}
        
        STRATEGY (T+1):
        1. ENTER: Market Open (09:55) Today.
        2. HOLD: Overnight.
        3. EXIT: Market Close (18:05) TOMORROW.
        4. STOP LOSS: Move to Breakeven at 18:00 Today.
        
        Good hunting.
        """
        send_email_alert(subject, body)
    else:
        print("No signal generated.")

if __name__ == "__main__":
    main()
