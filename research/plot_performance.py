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
    
    # Calculate Signals
    df['Z_Score'] = (df['SearchVolume'] - df['SearchVolume'].rolling(30).mean()) / df['SearchVolume'].rolling(30).std()
    df['SMA20'] = df['Close'].rolling(20).mean()
    
    return df

def run_best_strategy(df):
    # Best Params: LONG | Z > 1.5, Lag 1, Hold 3, Filter: None
    threshold = 1.5
    lag = 1
    hold = 3
    
    capital = 10000.0
    position = 0 
    equity_curve = [capital]
    
    prices = df['Close'].values
    signals = df['Z_Score'].values
    
    days_held = 0
    entry_price = 0
    
    for i in range(len(df)-1):
        current_equity = equity_curve[-1]
        
        # Exit
        if position == 1:
            days_held += 1
            if days_held >= hold:
                pnl = (prices[i] - entry_price) / entry_price * capital
                current_equity += pnl
                position = 0
                equity_curve.append(current_equity)
                continue
        
        # Entry
        idx = i - lag
        if idx >= 0 and position == 0:
            if signals[idx] > threshold:
                position = 1
                entry_price = prices[i]
                days_held = 0
        
        equity_curve.append(current_equity)
        
    # Benchmark
    benchmark = (df['Close'] / df['Close'].iloc[0]) * 10000
    
    # Plot
    plt.figure(figsize=(12, 6))
    plt.plot(equity_curve, label='Strategy (Long Impulse)', color='green')
    plt.plot(benchmark.values, label='Benchmark (BIST 30)', color='gray', linestyle='--')
    plt.title('Strategy Performance: "Halka Arz" Momentum')
    plt.legend()
    plt.grid(True)
    plt.savefig('strategy_performance.png')
    print("Saved strategy_performance.png")

if __name__ == "__main__":
    df = load_data()
    run_best_strategy(df)
