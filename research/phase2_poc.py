import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from cassandra.engine import CassandraEngine
from cassandra.models import SignalStatus, DetectionMethod

def load_and_process_bist(filepath="bist30.csv"):
    # yfinance saves with multi-level headers. The actual header is on line 3 (index 2)
    df = pd.read_csv(filepath, header=2)
    # Rename columns by index to be safe
    # Col 0 is Date, Col 1 is Close (usually)
    print(f"Columns found: {df.columns.tolist()}")
    df.columns.values[0] = "Date"
    df.columns.values[1] = "Close"
    
    # Drop the first few rows if they are metadata (NaNs in Close)
    df = df.dropna(subset=['Close'])
    
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').reset_index(drop=True)
    
    # Fill missing values if any
    df['Close'] = df['Close'].ffill()
    
    # Calculate Log Returns
    df['LogReturn'] = np.log(df['Close'] / df['Close'].shift(1))
    df['LogReturn'] = df['LogReturn'].fillna(0)
    
    # Invert Log Returns so 'Drops' become 'Positive Spikes'
    # This helps DTW match 'High Search Volume' (Spike) with 'Market Drop' (now Spike)
    df['PanicMetric'] = -1 * df['LogReturn']
    
    return df

def load_real_trends(filepath="trends.csv"):
    print("Loading Real 'Halka Arz' Search Volume...")
    df = pd.read_csv(filepath)
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').reset_index(drop=True)
    return df

def main():
    print("--- CASSANDRA PHASE 2.5: REALITY CHECK ---")
    
    # 1. Load BIST 30 Data (Real)
    print("Loading BIST 30 Data...")
    bist_df = load_and_process_bist()
    print(f"Loaded {len(bist_df)} days of data.")
    
    # 2. Load Real Trends Data
    trends_df = load_real_trends()
    
    # 3. Merge Data
    # We need to align dates.
    merged_df = pd.merge(bist_df, trends_df, on='Date', how='inner')
    print(f"Merged Data Points: {len(merged_df)}")
    
    # 4. Prepare Series for Cassandra
    # Target: Panic Metric (Inverted Log Returns of BIST 30)
    # We want to match "Search Spike" with "Panic Spike"
    # Panic Metric = -1 * Log Return. (Drop = Positive Spike)
    bist_series = merged_df['PanicMetric'].values
    
    # Source: Search Volume
    search_series = merged_df['Halka Arz'].values
    
    # 5. Run Cassandra Engine
    print("Running Cassandra Engine...")
    
    # Configure Engine
    # Layer 1 (Spearman): We expect this to be low because of the lag.
    # Layer 3 (DTW): We expect this to be high.
    config = {
        'layer1_threshold': 0.1, # Set low to ensure it passes to DTW if linear is weak
        'layer3_dist_threshold': 0.25, # Normalized distance threshold
        'layer3_radius': 7 # Look for matches within 7 days window
    }
    
    engine = CassandraEngine(config)
    
    # Analyze
    result = engine.analyze_pair(search_series, bist_series, name="HalkaArz_vs_BIST30")
    
    # 6. Report
    print("\n--- REPORT ---")
    print(f"Signal Status: {result.status.name}")
    print(f"Detection Method: {result.method.name}")
    print(f"Confidence Score: {result.confidence_score:.4f}")
    print(f"Metadata: {result.metadata}")
    
    if result.status == SignalStatus.FOUND and result.method == DetectionMethod.DTW:
        print("\nSUCCESS: System detected the delayed relationship via DTW!")
        print("Hypothesis Confirmed: Real Search Volume spikes precede Market Drops.")
    else:
        print("\nFAILURE: Could not detect relationship with Real Data.")
        print("Hypothesis Unconfirmed or Signal too weak.")

if __name__ == "__main__":
    main()
