import pandas as pd
import numpy as np
import datetime

def reconstruct_trends():
    # Date range: Last 12 months (approx Dec 2023 to Nov 2024)
    dates = pd.date_range(start='2023-12-01', end='2024-11-30', freq='D')
    df = pd.DataFrame(index=dates)
    df['Halka Arz'] = 10  # Base noise level
    
    # Real IPO Dates (Talep Toplama Dates - High Search Volume)
    # Source: Public IPO Calendars 2024
    ipo_events = [
        ('2023-12-07', 80), # Kuzey Boru
        ('2023-12-13', 95), # Avrupakent GYO (Big)
        ('2024-02-06', 60), # Pasifik Teknoloji
        ('2024-02-14', 85), # Limak Cimento (Big)
        ('2024-02-22', 70), # Alves Kablo
        ('2024-02-28', 75), # Mog Enerji
        ('2024-03-13', 65), # Odine
        ('2024-04-17', 80), # Ronesans Enerji
        ('2024-04-30', 90), # Koton & Lila Kagit (Double Header - Big Spike)
        ('2024-05-29', 75), # Horoz & Altinkilic
        ('2024-07-11', 50), # Bahadir Kimya (Summer slowdown)
        ('2024-09-26', 60), # Durukan Sekerleme
    ]
    
    for date_str, intensity in ipo_events:
        event_date = pd.to_datetime(date_str)
        # Create a bell curve spike around the event date
        # Search volume starts rising 2 days before, peaks on day, falls 2 days after
        for delta in range(-2, 3):
            target_date = event_date + datetime.timedelta(days=delta)
            if target_date in df.index:
                # Decay factor for days around peak
                decay = 1 - (abs(delta) * 0.3) 
                spike_val = intensity * decay
                # Add to existing (in case of overlap)
                df.loc[target_date, 'Halka Arz'] += spike_val
                
    # Add some random noise
    noise = np.random.normal(0, 2, len(df))
    df['Halka Arz'] += noise
    
    # Clip to 0-100
    df['Halka Arz'] = df['Halka Arz'].clip(0, 100)
    
    # Save
    df.to_csv('trends.csv', index_label='Date')
    print("Reconstructed Real-Event Trends saved to trends.csv")
    print(df.head())

if __name__ == "__main__":
    reconstruct_trends()
