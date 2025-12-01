import pandas as pd
import numpy as np

def inspect_data():
    trends = pd.read_csv("multiTimeline.csv", header=2)
    trends.columns = ['Date', 'SearchVolume']
    trends['Date'] = pd.to_datetime(trends['Date'])
    trends = trends.set_index('Date').resample('D').ffill().reset_index()
    
    bist = pd.read_csv("bist30.csv", header=2)
    bist.columns.values[0] = "Date"
    bist.columns.values[1] = "Close"
    bist = bist.dropna(subset=['Close'])
    bist['Date'] = pd.to_datetime(bist['Date'])
    bist = bist.sort_values('Date').reset_index(drop=True)
    bist['Close'] = bist['Close'].ffill()
    
    df = pd.merge(bist, trends, on='Date', how='inner')
    
    print("--- HEAD ---")
    print(df.head(10))
    
    print("\n--- CORRELATION ---")
    # Check correlation at different lags
    for lag in range(0, 10):
        corr = df['SearchVolume'].corr(df['Close'].shift(-lag))
        print(f"Lag {lag}: {corr:.4f}")

if __name__ == "__main__":
    inspect_data()
