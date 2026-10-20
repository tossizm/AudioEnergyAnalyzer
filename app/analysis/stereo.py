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
    """Compute per-band L/R correlation from one FFT per channel.

    Frequency-bin cross-products provide the zero-lag correlation of each
    band-limited signal without filtering the full audio separately 20 times.
    """
    if x.shape[1] == 1:
        return [1.0 for _ in bands]
    left=np.asarray(x[:,0],dtype=np.float64)
    right=np.asarray(x[:,1],dtype=np.float64)
    left=left-np.mean(left); right=right-np.mean(right)
    lf=np.fft.rfft(left); rf=np.fft.rfft(right)
    freqs=np.fft.rfftfreq(len(left),1.0/float(sr))
    cross=np.real(lf*np.conjugate(rf))
    lp=np.abs(lf)**2; rp=np.abs(rf)**2
    out=[]
    for lo,hi,_name in bands:
        mask=(freqs>=float(lo))&(freqs<min(float(hi),float(sr)/2.0))
        denom=float(np.sqrt(np.sum(lp[mask])*np.sum(rp[mask])))
        out.append(float(np.clip(np.sum(cross[mask])/denom,-1.0,1.0)) if denom>1e-24 else 0.0)
    return out

def low_band_correlation(x, sr, cutoff=120):
    """Compute low-band L/R correlation from FFT-domain quantities."""
    if x.shape[1] == 1:
        return 1.0
    left=np.asarray(x[:,0],dtype=np.float64)
    right=np.asarray(x[:,1],dtype=np.float64)
    left=left-np.mean(left); right=right-np.mean(right)
    lf=np.fft.rfft(left); rf=np.fft.rfft(right)
    freqs=np.fft.rfftfreq(len(left),1.0/float(sr))
    mask=freqs<=float(cutoff)
    cross=float(np.sum(np.real(lf[mask]*np.conjugate(rf[mask]))))
    lp=float(np.sum(np.abs(lf[mask])**2)); rp=float(np.sum(np.abs(rf[mask])**2))
    denom=float(np.sqrt(lp*rp))
    return float(np.clip(cross/denom,-1.0,1.0)) if denom>1e-24 else 0.0
