import numpy as np
import pandas as pd
from cassandra.engine import CassandraEngine
from cassandra.models import SignalStatus

def generate_synthetic_data(length=100):
    t = np.linspace(0, 10, length)
    
    # 1. Target: Stock Price (Random Walk + Trend)
    target = np.cumsum(np.random.randn(length)) + t * 2
    
    # 2. Candidate A: Linear Correlation (Target + Noise)
    candidate_linear = target + np.random.normal(0, 2, length)
    
    # 3. Candidate B: Non-Linear (U-shape relation to trend)
    # Let's make it related to 't' but quadratic, so it has a relation to target's trend
    candidate_nonlinear = (t - 5)**2 
    # This might not correlate well with 'target' directly unless target is also quadratic.
    # Let's make candidate B = target^2 (normalized)
    candidate_nonlinear_2 = target**2
    
    # 4. Candidate C: Time Warped (Shifted/Stretched)
    # Shift by 5 steps
    candidate_warped = np.roll(target, 5)
    candidate_warped[:5] = target[:5] # Fix edge
    
    # 5. Candidate D: Noise
    candidate_noise = np.random.randn(length)
    
    return target, {
        "Linear_Strong": candidate_linear,
        "NonLinear_Squared": candidate_nonlinear_2,
        "TimeWarped_Lag5": candidate_warped,
        "Pure_Noise": candidate_noise
    }

def main():
    print("Initializing Cassandra Engine...")
    engine = CassandraEngine(config={
        'layer1_threshold': 0.7,
        'layer2_threshold': 0.3,
        'layer3_dist_threshold': 0.2
    })
    
    print("Generating Synthetic Data...")
    target, candidates = generate_synthetic_data()
    
    print(f"Target Length: {len(target)}")
    print(f"Candidates: {list(candidates.keys())}")
    
    print("\nStarting Scan...")
    results = engine.scan(target, candidates)
    
    print("\nResults:")
    for name, result in results.items():
        status_icon = "✅" if result.status == SignalStatus.FOUND else "❌"
        method = result.method.value if result.method else "N/A"
        print(f"{status_icon} {name}: {result.status.value} | Method: {method} | Conf: {result.confidence_score:.4f}")
        if result.metadata:
            print(f"   Metadata: {result.metadata}")

if __name__ == "__main__":
    main()
