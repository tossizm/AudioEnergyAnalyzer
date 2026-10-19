import numpy as np
from scipy.signal import butter, sosfiltfilt

def correlation(x):
    if x.shape[1] == 1:
        return 1.0
    l, r = x[:,0], x[:,1]
    if np.std(l) < 1e-12 or np.std(r) < 1e-12:
        return 0.0
    return float(np.corrcoef(l, r)[0,1])

def _band_filter(sig, sr, lo, hi):
    nyq = sr * 0.5
    hi_eff = min(float(hi), nyq * 0.98)
    lo_eff = max(float(lo), 0.1)
    if hi_eff <= lo_eff or len(sig) < 32:
        return None
    sos = butter(4, [lo_eff, hi_eff], btype="bandpass", fs=sr, output="sos")
    return sosfiltfilt(sos, sig)

def band_correlations(x, sr, bands):
    """Return Pearson L/R correlation for each configured frequency band."""
    if x.shape[1] == 1:
        return [1.0 for _ in bands]
    out=[]
    for lo, hi, _name in bands:
        l=_band_filter(x[:,0], sr, lo, hi)
        r=_band_filter(x[:,1], sr, lo, hi)
        if l is None or r is None or np.std(l)<1e-12 or np.std(r)<1e-12:
            out.append(0.0)
        else:
            out.append(float(np.corrcoef(l,r)[0,1]))
    return out

def low_band_correlation(x, sr, cutoff=120):
    if x.shape[1] == 1:
        return 1.0
    n = len(x)
    freqs = np.fft.rfftfreq(n, 1/sr)
    def low(sig):
        spec = np.fft.rfft(sig)
        spec[freqs > cutoff] = 0
        return np.fft.irfft(spec, n=n)
    return correlation(np.column_stack([low(x[:,0]), low(x[:,1])]))
