from dataclasses import dataclass
from enum import Enum
from typing import Optional

class SignalStatus(Enum):
    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"

class SignalType(Enum):
    PARALLEL = "PARALLEL"
    INVERSE = "INVERSE"

class DetectionMethod(Enum):
    SPEARMAN = "SPEARMAN"
    MUTUAL_INFO = "MUTUAL_INFO"
    DTW = "DTW"

@dataclass
class SignalResult:
    status: SignalStatus
    method: Optional[DetectionMethod] = None
    confidence_score: float = 0.0
    detected_lag: int = 0 # In days/units
    estimated_impact: float = 0.0 # Expected % change
    action_recommendation: str = "" # e.g., "SHORT", "WAIT"
    signal_type: Optional[SignalType] = None
    metadata: Optional[dict] = None
