import numpy as np
from sklearn.feature_selection import mutual_info_regression
from ..models import SignalResult, SignalStatus, SignalType, DetectionMethod

class Layer2MutualInfo:
    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold

    def analyze(self, x: np.ndarray, y: np.ndarray) -> SignalResult:
        """
        Non-linear relationship check using Mutual Information.
        """
        # Reshape for sklearn
        x_reshaped = x.reshape(-1, 1)
        
        # Calculate MI score
        # discrete_features=False because we assume continuous data
        mi_score = mutual_info_regression(x_reshaped, y, discrete_features=False)[0]
        
        # Normalize MI score roughly to 0-1 range for consistency (though MI can be > 1)
        # For this context, we treat the raw score as the confidence if it's within expected bounds,
        # or we could normalize it against the entropy of the signals. 
        # For simplicity and speed, we'll use the raw score and a calibrated threshold.
        # A high MI score indicates dependency.
        
        if mi_score >= self.threshold:
            return SignalResult(
                status=SignalStatus.FOUND,
                method=DetectionMethod.MUTUAL_INFO,
                confidence_score=mi_score, # Note: MI is not strictly 0-1
                detected_lag=0,
                signal_type=SignalType.PARALLEL, # MI doesn't distinguish direction easily, assume parallel for now or need extra check
                metadata={"raw_mi_score": mi_score}
            )

        return SignalResult(status=SignalStatus.NOT_FOUND)
