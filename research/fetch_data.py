import yfinance as yf
from pytrends.request import TrendReq
import pandas as pd
import time

def fetch_data():
    print("Fetching BIST 30 data...")
    # XU030.IS is the ticker for BIST 30 Index
    bist30 = yf.download("XU030.IS", period="2y", interval="1d")
    
    if bist30.empty:
        print("Failed to fetch BIST 30 data.")
        return None, None
    
    print(f"BIST 30 data fetched: {len(bist30)} rows.")
    
    print("Fetching Google Trends data for 'Halka Arz'...")
    try:
        pytrends = TrendReq(hl='tr-TR', tz=180) # Turkey timezone
        kw_list = ["Halka Arz"]
        # timeframe='today 5-y' or specific dates. Let's try last 2 years.
        # 'today 12-m' is last 12 months. 'today 5-y' is 5 years.
        # Custom timeframe: '2023-01-01 2024-12-01'
        pytrends.build_payload(kw_list, cat=0, timeframe='2023-01-01 2024-12-01', geo='TR')
        trends = pytrends.interest_over_time()
        
        if trends.empty:
            print("Google Trends returned empty data.")
            return bist30, None
            
        print(f"Trends data fetched: {len(trends)} rows.")
        return bist30, trends
        
    except Exception as e:
        print(f"Error fetching Google Trends: {e}")
        return bist30, None

if __name__ == "__main__":
    bist, trends = fetch_data()
    if bist is not None:
        bist.to_csv("bist30.csv")
    if trends is not None:
        trends.to_csv("trends.csv")
