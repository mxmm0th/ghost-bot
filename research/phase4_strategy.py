import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from itertools import product

def load_data():
    # Load Trends
    trends = pd.read_csv("multiTimeline.csv", header=2)
    trends.columns = ['Date', 'SearchVolume']
    trends['Date'] = pd.to_datetime(trends['Date'])
    trends = trends.set_index('Date').resample('D').ffill().reset_index()
    
    # Load BIST 30
    bist = pd.read_csv("bist30.csv", header=2)
    bist.columns.values[0] = "Date"
    bist.columns.values[1] = "Close"
    bist = bist.dropna(subset=['Close'])
    bist['Date'] = pd.to_datetime(bist['Date'])
    bist = bist.sort_values('Date').reset_index(drop=True)
    bist['Close'] = bist['Close'].ffill()
    
    # Merge
    df = pd.merge(bist, trends, on='Date', how='inner')
    return df

def calculate_signals(df, window=30):
    # Feature Engineering
    rolling_mean = df['SearchVolume'].rolling(window=window).mean()
    rolling_std = df['SearchVolume'].rolling(window=window).std()
    df['Z_Score'] = (df['SearchVolume'] - rolling_mean) / rolling_std
    
    # Trend Indicators
    df['SMA20'] = df['Close'].rolling(window=20).mean()
    df['SMA50'] = df['Close'].rolling(window=50).mean()
    
    return df

def backtest_strategy(df, threshold, entry_lag, holding_period, trend_filter=None, direction='SHORT', signal_col='Z_Score'):
    """
    Simulates trading based on the signal.
    """
    capital = 10000.0
    position = 0 
    entry_price = 0.0
    days_held = 0
    equity_curve = [capital]
    trades = []
    
    n = len(df)
    signals = df[signal_col].values
    prices = df['Close'].values
    dates = df['Date'].values
    sma20 = df['SMA20'].values
    sma50 = df['SMA50'].values
    
    i = 0
    while i < n - 1:
        current_equity = equity_curve[-1]
        
        # Check Exit
        if position != 0:
            days_held += 1
            if days_held >= holding_period:
                exit_price = prices[i]
                if position == 1: # Long
                    pnl = (exit_price - entry_price) / entry_price * capital
                else: # Short
                    pnl = (entry_price - exit_price) / entry_price * capital
                    
                current_equity += pnl
                position = 0
                trades.append({'EntryDate': entry_date, 'ExitDate': dates[i], 'Type': direction, 'PnL': pnl, 'Return': pnl/capital})
                equity_curve.append(current_equity)
                i += 1
                continue
            else:
                equity_curve.append(current_equity)
                i += 1
                continue
        
        # Check Entry
        signal_idx = i - entry_lag
        if signal_idx >= 0 and position == 0:
            signal_condition = signals[signal_idx] > threshold
            
            # Trend Filter
            trend_condition = True
            if trend_filter == 'SMA20':
                if np.isnan(sma20[i]): trend_condition = False
                elif direction == 'SHORT' and prices[i] > sma20[i]: trend_condition = False # Don't short uptrend
                elif direction == 'LONG' and prices[i] < sma20[i]: trend_condition = False # Don't buy downtrend
            
            if signal_condition and trend_condition:
                if direction == 'SHORT':
                    position = -1
                else:
                    position = 1
                entry_price = prices[i]
                entry_date = dates[i]
                days_held = 0
                equity_curve.append(current_equity)
                i += 1
                continue
        
        equity_curve.append(current_equity)
        i += 1
        
    return equity_curve, trades

def optimize():
    print("Loading Data...")
    df = load_data()
    df = calculate_signals(df, window=30)
    df = df.dropna()
    
    # Grid Search Space
    thresholds = [1.5, 2.0, 2.5] 
    lags = [1, 3, 5] 
    holding_periods = [3, 5, 10]
    trend_filters = [None, 'SMA20']
    directions = ['SHORT', 'LONG'] # Test both
    
    best_perf = -np.inf
    best_params = None
    results = []
    
    print("\nRunning Optimization (Long & Short)...")
    for thresh, lag, hold, trend, direct in product(thresholds, lags, holding_periods, trend_filters, directions):
        equity, trades = backtest_strategy(df, thresh, lag, hold, trend_filter=trend, direction=direct)
        
        if not trades:
            continue
            
        final_equity = equity[-1]
        total_return = (final_equity - 10000) / 10000
        num_trades = len(trades)
        
        results.append({
            'Direction': direct,
            'Threshold': thresh,
            'Lag': lag,
            'Hold': hold,
            'Filter': trend,
            'Return': total_return,
            'Trades': num_trades
        })
        
        if total_return > best_perf:
            best_perf = total_return
            best_params = (thresh, lag, hold, trend, direct)
    
    # Report Best
    results_df = pd.DataFrame(results).sort_values('Return', ascending=False)
    print("\n--- TOP 5 STRATEGIES ---")
    print(results_df.head(5))
    
    best_params = results_df.iloc[0]
    print(f"\nBEST PARAMETERS: {best_params['Direction']} | Z > {best_params['Threshold']}, Lag {best_params['Lag']}, Hold {best_params['Hold']}, Filter: {best_params['Filter']}")
    print(f"Best Return: {best_params['Return']*100:.2f}%")
    
    # Detailed Run for Best Strategy to get Risk Metrics
    equity, trades = backtest_strategy(df, best_params['Threshold'], int(best_params['Lag']), int(best_params['Hold']), trend_filter=best_params['Filter'], direction=best_params['Direction'])
    
    # Calculate Risk Metrics
    equity_series = pd.Series(equity)
    returns = equity_series.pct_change().dropna()
    sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if returns.std() != 0 else 0
    
    running_max = equity_series.cummax()
    drawdown = (equity_series - running_max) / running_max
    max_drawdown = drawdown.min()
    
    print(f"Sharpe Ratio: {sharpe_ratio:.2f}")
    print(f"Max Drawdown: {max_drawdown*100:.2f}%")
    
    print("\n--- TRADE LOG (Best Strategy) ---")
    trades_df = pd.DataFrame(trades)
    print(trades_df)

    # Benchmark
    start_price = df['Close'].iloc[0]
    end_price = df['Close'].iloc[-1]
    bh_return = (end_price - start_price) / start_price
    print(f"\nBenchmark (Buy & Hold) Return: {bh_return*100:.2f}%")

if __name__ == "__main__":
    optimize()
