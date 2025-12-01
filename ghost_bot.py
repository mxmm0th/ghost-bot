import os
import sys
import pandas as pd
import requests
from pytrends.request import TrendReq

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email_alert(subject, body):
    sender_email = os.environ.get("EMAIL_USER")
    sender_password = os.environ.get("EMAIL_PASSWORD")
    receiver_email = "vojerkan@gmail.com"
    
    if not sender_email or not sender_password:
        print("Error: Email credentials not found in environment variables.")
        return
        
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        # Connect to Gmail SMTP
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)
        server.quit()
        print(f"Email alert sent to {receiver_email}")
    except Exception as e:
        print(f"Error sending email: {e}")

def main():
    print("--- GHOST BOT: STARTED ---")
    
    # 1. Fetch Data (Last 90 Days)
    try:
        print("Fetching Google Trends data...")
        pytrends = TrendReq(hl='tr-TR', tz=180)
        kw_list = ["Halka Arz"]
        # 'today 3-m' fetches last 3 months
        pytrends.build_payload(kw_list, cat=0, timeframe='today 3-m', geo='TR', gprop='')
        df = pytrends.interest_over_time()
        
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
        subject = "🚨 ALARM: BIST 30 Momentum Sinyali"
        body = f"""
        GHOST BOT REPORT
        ----------------
        Sinyal: MOMENTUM LONG (Halka Arz İlgisi)
        
        Z-Score: {z_score:.2f} (Eşik: {THRESHOLD})
        Güncel Değer: {latest_val}
        
        ACTION:
        -> BUY BIST 30
        -> HOLD: 3 Gün
        
        Bu otomatik bir mesajdır.
        """
        
        print("Signal Detected! Sending Email Alert...")
        send_email_alert(subject, body)
    else:
        print("No Signal. Z-Score is below threshold.")

if __name__ == "__main__":
    main()
