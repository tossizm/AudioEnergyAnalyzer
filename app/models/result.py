from dataclasses import dataclass
from typing import List

@dataclass
class BandResult:
    name: str
    low: float
    high: float
    energy_occupancy_pct: float
    post_energy_occupancy_pct: float
    sample_db: float
    target_db: float
    diff_db: float
    status: str
    priority: str

@dataclass
class EQRecommendation:
    filter_type: str
    frequency: float
    gain_db: float
    q: float

@dataclass
class AnalysisResult:
    filename: str
    sample_rate: int
    duration: float
    stereo_correlation: float
    bass_mono_hz: int
    bands: List[BandResult]
    eq: List[EQRecommendation]
    overall: str
    peak_dbfs: float = 0.0
    true_peak_dbtp: float = 0.0
    rms_dbfs: float = 0.0
    integrated_lufs: float = 0.0
    crest_factor_db: float = 0.0
    band_correlations: List[float] = None
    audio_created_at: str = ""
    config_filename: str = ""
    bitrate_kbps: int | None = None
    analysis_elapsed_seconds: float = 0.0
