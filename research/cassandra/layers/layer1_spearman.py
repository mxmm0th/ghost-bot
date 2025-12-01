import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from ..models import SignalResult, SignalStatus, SignalType, DetectionMethod

class Layer1Spearman:
    def __init__(self, threshold: float = 0.7, p_value_threshold: float = 0.05):
        self.threshold = threshold
        self.p_value_threshold = p_value_threshold

    def analyze(self, x: np.ndarray, y: np.ndarray) -> SignalResult:
        """
        Fast linear/monotonic relationship check using Spearman correlation.
        """
        # Spearman correlation is resistant to outliers and non-normal distributions
        corr, p_value = spearmanr(x, y)

        # Handle NaN results
        if np.isnan(corr):
            return SignalResult(status=SignalStatus.NOT_FOUND)

        if p_value < self.p_value_threshold and abs(corr) >= self.threshold:
            signal_type = SignalType.PARALLEL if corr > 0 else SignalType.INVERSE
            return SignalResult(
                status=SignalStatus.FOUND,
                method=DetectionMethod.SPEARMAN,
                confidence_score=abs(corr),
                detected_lag=0, # Spearman doesn't detect lag by itself
                signal_type=signal_type,
                metadata={"p_value": p_value}
            )
        
        return SignalResult(status=SignalStatus.NOT_FOUND)
