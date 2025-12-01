import pandas as pd
import numpy as np
from cassandra.engine import CassandraEngine
from cassandra.models import SignalStatus, DetectionMethod

def load_real_trends(filepath="multiTimeline.csv"):
    print(f"Loading Real Trends from {filepath}...")
    # Read CSV, skipping first 2 lines (header is on line 3)
    df = pd.read_csv(filepath, header=2)
    
    # Rename columns: 'Hafta' -> 'Date', 'halka arz: (Türkiye)' -> 'Halka Arz'
    # We assume column 0 is Date, column 1 is Value
    df.columns = ['Date', 'Halka Arz']
    
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.set_index('Date')
    
    # Resample to Daily to match BIST trading days (Forward Fill weekly data)
    df = df.resample('D').ffill().reset_index()
    
    return df

def load_and_process_bist(filepath="bist30.csv"):
    df = pd.read_csv(filepath, header=2)
    # Rename columns by index to be safe
    df.columns.values[0] = "Date"
    df.columns.values[1] = "Close"
    df = df.dropna(subset=['Close'])
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').reset_index(drop=True)
    df['Close'] = df['Close'].ffill()
    df['LogReturn'] = np.log(df['Close'] / df['Close'].shift(1))
    df['LogReturn'] = df['LogReturn'].fillna(0)
    df['PanicMetric'] = -1 * df['LogReturn']
    return df

def main():
    print("--- CASSANDRA PHASE 3: DETAILED SIGNAL ANALYSIS ---")
    
    # Load Data
    bist_df = load_and_process_bist()
    trends_df = load_real_trends()
    merged_df = pd.merge(bist_df, trends_df, on='Date', how='inner')
    
    bist_series = merged_df['PanicMetric'].values
    search_series = merged_df['Halka Arz'].values
    
    # Configure Engine
    config = {
        'layer1_threshold': 0.1, 
        'layer3_dist_threshold': 0.25, 
        'layer3_radius': 7 
    }
    
    engine = CassandraEngine(config)
    
    # Analyze
    result = engine.analyze_pair(search_series, bist_series, name="HalkaArz_vs_BIST30")
    
    # Detailed Report
    print("\n--- ACTIONABLE INTELLIGENCE REPORT ---")
    if result.status == SignalStatus.FOUND:
        print(f"SIGNAL DETECTED via {result.method.name}")
        print(f"Confidence: {result.confidence_score*100:.1f}%")
        print("-" * 30)
        print(f"DETECTED LAG: {result.detected_lag} Days")
        print(f"  -> Interpretation: Market reacts {result.detected_lag} days AFTER the search spike.")
        print("-" * 30)
        print(f"ESTIMATED IMPACT: {result.estimated_impact:.4f} (Relative Scale)")
        print(f"  -> Interpretation: Positive value means Market Drop (Panic) follows Search Spike.")
        print("-" * 30)
        print(f"RECOMMENDATION: {result.action_recommendation}")
        
        if result.detected_lag > 0:
            print(f"  -> ACTION: Monitor 'Halka Arz' trends. If spike occurs, SHORT BIST 30 within {result.detected_lag} days.")
    else:
        print("No actionable signal found.")

if __name__ == "__main__":
    main()
