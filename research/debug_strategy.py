import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def load_data():
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
    return df

def plot_debug(df):
    # Calculate Z-Score
    df['Z_Score'] = (df['SearchVolume'] - df['SearchVolume'].rolling(30).mean()) / df['SearchVolume'].rolling(30).std()
    
    fig, ax1 = plt.subplots(figsize=(12, 6))
    
    color = 'tab:blue'
    ax1.set_xlabel('Date')
    ax1.set_ylabel('BIST 30 Price', color=color)
    ax1.plot(df['Date'], df['Close'], color=color, label='Price')
    ax1.tick_params(axis='y', labelcolor=color)
    
    ax2 = ax1.twinx()  
    color = 'tab:red'
    ax2.set_ylabel('Search Z-Score', color=color)
    ax2.plot(df['Date'], df['Z_Score'], color=color, alpha=0.6, label='Search Z-Score')
    ax2.axhline(2.0, color='gray', linestyle='--', alpha=0.5)
    ax2.tick_params(axis='y', labelcolor=color)
    
    plt.title('BIST 30 Price vs Search Volume Z-Score')
    plt.savefig('debug_plot.png')
    print("Saved debug_plot.png")

if __name__ == "__main__":
    df = load_data()
    plot_debug(df)
