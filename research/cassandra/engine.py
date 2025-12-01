import numpy as np
import pandas as pd
from typing import List, Tuple, Dict
from joblib import Parallel, delayed

from .models import SignalResult, SignalStatus, DetectionMethod
from .preprocessor import DataPreprocessor
from .layers.layer1_spearman import Layer1Spearman
from .layers.layer2_mutual_info import Layer2MutualInfo
from .layers.layer3_dtw import Layer3DTW

class CassandraEngine:
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.preprocessor = DataPreprocessor()
        
        # Initialize Layers with config
        self.layer1 = Layer1Spearman(
            threshold=self.config.get('layer1_threshold', 0.7),
            p_value_threshold=self.config.get('layer1_p_value', 0.05)
        )
        self.layer2 = Layer2MutualInfo(
            threshold=self.config.get('layer2_threshold', 0.3) # Lower threshold for MI
        )
        self.layer3 = Layer3DTW(
            max_distance_threshold=self.config.get('layer3_dist_threshold', 0.2), # Normalized distance
            radius=self.config.get('layer3_radius', 5)
        )
        
        # Layer 1 lower bound to decide if we should proceed to Layer 2
        # If correlation is very low (e.g. < 0.1), we might skip L2/L3 to save time,
        # UNLESS we strictly want to find non-linear relationships even if linear is 0.
        # The prompt says "Fail-Fast", implying we drop things.
        # But U-shape has 0 linear correlation.
        # So maybe we use a very loose filter for "potential"?
        # Or maybe we just check everything that isn't "Found" in L1?
        # For performance, let's assume we proceed if it's not "Found" but not "Zero".
        self.layer1_prune_threshold = self.config.get('layer1_prune_threshold', 0.1)

    def analyze_pair(self, x: np.ndarray, y: np.ndarray, name: str = "pair") -> SignalResult:
        """
        Run the 3-stage cascade on a single pair of data.
        """
        # 0. Preprocessing
        # Assume x and y are already aligned in time (same length)
        # We normalize them here to ensure layers work correctly
        x_norm = self.preprocessor.prepare_series(x, normalize=True, stationarity_method=None)
        y_norm = self.preprocessor.prepare_series(y, normalize=True, stationarity_method=None)
        
        # 1. Layer 1: Speed Gate (Spearman)
        result_l1 = self.layer1.analyze(x_norm, y_norm)
        if result_l1.status == SignalStatus.FOUND:
            return result_l1
        
        # Fail-Fast check
        # If correlation is extremely weak, we might stop here.
        # But we need to be careful about non-linear signals.
        # Let's check the confidence (abs correlation) from L1.
        # If it's < prune_threshold, we stop.
        # Note: L1 returns NOT_FOUND with 0 confidence if not found, 
        # so we might need to peek at the raw correlation if we want to prune.
        # For now, let's assume we proceed to L2 if L1 didn't find a strong linear match.
        # To strictly follow "Fail-Fast", we should prune.
        # But to find "Hidden" signals, we shouldn't prune too aggressively based on linearity.
        # Let's proceed to L2.
        
        # 2. Layer 2: Deep Analysis (Mutual Information)
        result_l2 = self.layer2.analyze(x_norm, y_norm)
        if result_l2.status == SignalStatus.FOUND:
            return result_l2
            
        # 3. Layer 3: Elastic Time (DTW)
        # Only if L2 didn't find anything (or maybe we want to check DTW anyway?)
        # Cascade model implies we stop if found.
        result_l3 = self.layer3.analyze(x_norm, y_norm)
        return result_l3

    def scan(self, target_series: np.ndarray, candidates: Dict[str, np.ndarray], n_jobs: int = -1) -> Dict[str, SignalResult]:
        """
        Scan a target series (e.g. Stock Price) against multiple candidates (e.g. Trends).
        Uses parallel processing.
        """
        results = Parallel(n_jobs=n_jobs)(
            delayed(self.analyze_pair)(target_series, candidate, name)
            for name, candidate in candidates.items()
        )
        
        return dict(zip(candidates.keys(), results))
