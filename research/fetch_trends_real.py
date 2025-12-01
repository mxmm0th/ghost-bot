from pytrends.request import TrendReq
import pandas as pd
import time
import random

def fetch_trends():
    print("Attempting to fetch Google Trends data for 'Halka Arz'...")
    try:
        # Simple connection
        pytrends = TrendReq(hl='tr-TR', tz=180)
        kw_list = ["Halka Arz"]
        
        # Build payload
        pytrends.build_payload(kw_list, cat=0, timeframe='today 12-m', geo='TR')
        
        # Get interest over time
        trends = pytrends.interest_over_time()
        
        if not trends.empty:
            print("Successfully fetched data!")
            if 'isPartial' in trends.columns:
                trends = trends.drop(columns=['isPartial'])
            
            # Save to CSV
            trends.to_csv('trends.csv')
            print("Saved to trends.csv")
            print(trends.head())
        else:
            print("Fetched data is empty.")
            
    except Exception as e:
        print(f"Error fetching data: {e}")

if __name__ == "__main__":
    fetch_trends()
