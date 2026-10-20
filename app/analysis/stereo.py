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
    """Compute band-wise L/R correlation from bounded-memory FFT chunks."""
    if x.shape[1] == 1:
        return [1.0 for _ in bands]
    block_size=262144
    cross_sum=np.zeros(len(bands),dtype=np.float64)
    left_power=np.zeros(len(bands),dtype=np.float64)
    right_power=np.zeros(len(bands),dtype=np.float64)
    for start in range(0,len(x),block_size):
        chunk=np.asarray(x[start:start+block_size],dtype=np.float64)
        if len(chunk)<32:
            continue
        left=chunk[:,0]-np.mean(chunk[:,0])
        right=chunk[:,1]-np.mean(chunk[:,1])
        lf=np.fft.rfft(left); rf=np.fft.rfft(right)
        freqs=np.fft.rfftfreq(len(chunk),1.0/float(sr))
        cross=np.real(lf*np.conjugate(rf))
        lp=np.abs(lf)**2; rp=np.abs(rf)**2
        for i,(lo,hi,_name) in enumerate(bands):
            mask=(freqs>=float(lo))&(freqs<min(float(hi),float(sr)/2.0))
            cross_sum[i]+=float(np.sum(cross[mask]))
            left_power[i]+=float(np.sum(lp[mask]))
            right_power[i]+=float(np.sum(rp[mask]))
    denom=np.sqrt(left_power*right_power)
    return [float(np.clip(cross_sum[i]/denom[i],-1.0,1.0)) if denom[i]>1e-24 else 0.0 for i in range(len(bands))]

def low_band_correlation(x, sr, cutoff=120):
    """Compute low-band L/R correlation using bounded-memory FFT chunks."""
    if x.shape[1] == 1:
        return 1.0
    cross_sum=left_power=right_power=0.0
    block_size=262144
    for start in range(0,len(x),block_size):
        chunk=np.asarray(x[start:start+block_size],dtype=np.float64)
        if len(chunk)<32:
            continue
        left=chunk[:,0]-np.mean(chunk[:,0])
        right=chunk[:,1]-np.mean(chunk[:,1])
        lf=np.fft.rfft(left); rf=np.fft.rfft(right)
        freqs=np.fft.rfftfreq(len(chunk),1.0/float(sr))
        mask=freqs<=float(cutoff)
        cross_sum+=float(np.sum(np.real(lf[mask]*np.conjugate(rf[mask]))))
        left_power+=float(np.sum(np.abs(lf[mask])**2))
        right_power+=float(np.sum(np.abs(rf[mask])**2))
    denom=float(np.sqrt(left_power*right_power))
    return float(np.clip(cross_sum/denom,-1.0,1.0)) if denom>1e-24 else 0.0
