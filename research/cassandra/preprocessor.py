import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

class DataPreprocessor:
    def __init__(self):
        self.scaler = MinMaxScaler(feature_range=(0, 1))

    def normalize(self, data: np.ndarray) -> np.ndarray:
        """
        Normalize data to 0-1 range using MinMax Scaling.
        Handles 1D arrays by reshaping.
        """
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        return self.scaler.fit_transform(data).flatten()

    def make_stationary(self, data: np.ndarray, method: str = 'diff') -> np.ndarray:
        """
        Make data stationary to avoid spurious correlations.
        Supported methods: 'diff' (first difference), 'log_return'.
        """
        if method == 'diff':
            return np.diff(data, prepend=data[0])
        elif method == 'log_return':
            # Handle zeros or negative values for log
            safe_data = np.where(data <= 0, 1e-9, data)
            log_ret = np.diff(np.log(safe_data), prepend=np.log(safe_data[0]))
            return log_ret
        else:
            raise ValueError(f"Unknown stationarity method: {method}")

    def prepare_series(self, series: np.ndarray, normalize: bool = True, stationarity_method: str = None) -> np.ndarray:
        """
        Full pipeline: Stationarity -> Normalization
        """
        processed = series.copy()
        
        if stationarity_method:
            processed = self.make_stationary(processed, method=stationarity_method)
            
        if normalize:
            processed = self.normalize(processed)
            
        return processed
