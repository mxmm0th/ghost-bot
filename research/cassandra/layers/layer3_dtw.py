import numpy as np
from fastdtw import fastdtw
from scipy.spatial.distance import euclidean
from ..models import SignalResult, SignalStatus, SignalType, DetectionMethod

class Layer3DTW:
    def __init__(self, max_distance_threshold: float = 10.0, radius: int = 10):
        self.max_distance_threshold = max_distance_threshold
        self.radius = radius

    def analyze(self, x: np.ndarray, y: np.ndarray) -> SignalResult:
        """
        Elastic time matching using Dynamic Time Warping (FastDTW).
        """
        # fastdtw requires 1D arrays or 2D
        # It returns distance and path
        # For 1D arrays, the distance between points is just abs(x-y)
        # scipy.spatial.distance.euclidean fails on scalars
        distance, path = fastdtw(x, y, radius=self.radius, dist=lambda a, b: abs(a - b))
        
        # Normalize distance by path length or array length to make it comparable?
        # A simple approach is to use the raw distance if inputs are normalized.
        # Since inputs are 0-1, the max distance depends on length.
        # Normalized distance = distance / len(path)
        normalized_distance = distance / len(path)
        
        # Lower distance means better match
        if normalized_distance <= self.max_distance_threshold:
            # Calculate a confidence score based on distance
            # 0 distance = 1.0 confidence
            # max_distance = 0.0 confidence (roughly)
            confidence = max(0.0, 1.0 - (normalized_distance / self.max_distance_threshold))
            
            # Calculate Lag from Path
            # Path is list of (x_idx, y_idx). Lag = y_idx - x_idx
            lags = [y_i - x_i for x_i, y_i in path]
            avg_lag = int(np.mean(lags))
            
            # Calculate Estimated Impact (Magnitude)
            # We look at the difference in values at the matched points
            # Since inputs are normalized, this is relative impact.
            # For real impact, we need original scales, but here we give a relative score.
            impacts = [y[y_i] - x[x_i] for x_i, y_i in path]
            avg_impact = float(np.mean(impacts))
            
            # Recommendation
            recommendation = "WAIT"
            if avg_lag > 0:
                recommendation = "PREPARE" # Signal leads price
            
            return SignalResult(
                status=SignalStatus.FOUND,
                method=DetectionMethod.DTW,
                confidence_score=confidence,
                detected_lag=avg_lag,
                estimated_impact=avg_impact,
                action_recommendation=recommendation,
                signal_type=SignalType.PARALLEL, 
                metadata={"dtw_distance": distance, "normalized_distance": normalized_distance}
            )

        return SignalResult(status=SignalStatus.NOT_FOUND)
