import numpy as np
import pyloudnorm as pyln
from pathlib import Path
from scipy.signal import stft, freqz
import soundfile as sf

DEFAULT_BANDS = [
    (20, 60, "20–60 Hz"), (60, 120, "60–120 Hz"),
    (120, 250, "120–250 Hz"), (250, 500, "250–500 Hz"),
    (500, 1000, "500–1000 Hz"), (1000, 2000, "1000–2000 Hz"),
    (2000, 4000, "2000–4000 Hz"), (4000, 8000, "4000–8000 Hz"),
    (8000, 16000, "8000–16000 Hz"), (16000, 20000, "16000–20000 Hz")
]
BANDS = list(DEFAULT_BANDS)


def set_band_maxima(maxima):
    """Set the nine editable upper edges; band 1 starts at 20 Hz and band 10 ends at 20000 Hz."""
    vals = [int(v) for v in maxima]
    if len(vals) != 9:
        raise ValueError("9個の最大Hz値が必要です。")
    previous = 20
    for v in vals:
        if v < 20 or v > 20000:
            raise ValueError("最大Hz値は20～20000の整数で指定してください。")
        if v <= previous:
            raise ValueError("最大Hz値は前の値より大きくしてください。")
        previous = v
    if vals[-1] >= 20000:
        raise ValueError("⑨の最大Hz値は20000未満にしてください。")
    edges = [20, *vals, 20000]
    BANDS[:] = [(edges[i], edges[i + 1], f"{edges[i]}–{edges[i + 1]} Hz") for i in range(10)]


def build_band_settings_payload(maxima):
    """Build the persisted 10-band configuration from the GUI's nine editable maxima."""
    vals=[int(v) for v in maxima]
    if len(vals)!=9:
        raise ValueError("9個の最大Hz値が必要です。")
    previous=20
    for v in vals:
        if v <= previous or v >= 20000:
            raise ValueError("最大Hz値は20～20000の範囲で昇順に指定してください。")
        previous=v
    edges=[20,*vals,20000]
    return {
        "version":"1.0",
        "bands":[{"min_hz":edges[i],"max_hz":edges[i+1]} for i in range(10)]
    }


def reset_bands():
    BANDS[:] = list(DEFAULT_BANDS)


def _load_compressed_with_pyav(path, progress=None):
    try:
        import av
    except Exception as e:
        raise RuntimeError("MP3デコーダ(PyAV)がアプリに含まれていません。再ビルドしてください。") from e

    try:
        container = av.open(str(path))
        stream = next((s for s in container.streams.audio), None)
        if stream is None:
            raise RuntimeError("オーディオストリームが見つかりません。")
        duration = None
        if stream.duration is not None and stream.time_base is not None:
            duration = float(stream.duration * stream.time_base)

        resampler = av.audio.resampler.AudioResampler(
            format="fltp", layout="stereo", rate=48000
        )
        chunks = []
        for frame in container.decode(stream):
            out_frames = resampler.resample(frame)
            if not isinstance(out_frames, list):
                out_frames = [out_frames]
            for out in out_frames:
                a = out.to_ndarray()
                if a.ndim == 1:
                    a = a.reshape(1, -1)
                if a.shape[0] != 2:
                    a = np.vstack([a[0:1], a[0:1]])
                chunks.append(a.T.astype(np.float32, copy=False))
            if progress and duration and frame.pts is not None and frame.time_base is not None:
                t = max(0.0, float(frame.pts * frame.time_base))
                progress(min(99, int(t / duration * 100)))
        tail = resampler.resample(None)
        if not isinstance(tail, list):
            tail = [tail]
        for out in tail:
            a = out.to_ndarray()
            if a.ndim == 1: a = a.reshape(1, -1)
            if a.shape[0] != 2: a = np.vstack([a[0:1], a[0:1]])
            chunks.append(a.T.astype(np.float32, copy=False))
        container.close()
    except Exception as e:
        raise RuntimeError(f"MP3デコードに失敗しました。\n{e}") from e

    if not chunks:
        raise RuntimeError("MP3からPCMデータを取得できませんでした。")
    x=np.vstack(chunks)
    if progress: progress(100)
    return x,48000


def _load_soundfile(path, progress=None):
    with sf.SoundFile(str(path)) as f:
        sr=f.samplerate; channels=f.channels; total=len(f)
        blocks=[]; done=0; block=16384
        while True:
            x=f.read(block,dtype="float32",always_2d=True)
            if len(x)==0: break
            blocks.append(x); done+=len(x)
            if progress and total: progress(min(100,int(done/total*100)))
    return np.vstack(blocks) if blocks else np.empty((0,channels),dtype=np.float32),sr


def load_audio(path: Path, progress=None):
    if path.suffix.lower()==".mp3":
        x,sr=_load_compressed_with_pyav(path,progress)
    else:
        x,sr=_load_soundfile(path,progress)
    if len(x)==0: raise RuntimeError("オーディオデータが空です。")
    x=x-np.mean(x,axis=0,keepdims=True)
    return x,sr


def _band_power_values(x, sr, progress=None):
    """Return measured linear spectral energy for each active band.

    The values are derived directly from the sample spectrum and are not
    compared with, normalized to, or influenced by any reference target.
    """
    mono=np.mean(x,axis=1)
    nperseg=min(65536,len(mono))
    if nperseg<1024: nperseg=len(mono)
    noverlap=int(nperseg*0.75) if nperseg>1 else 0
    f,_,z=stft(mono,fs=sr,window="hann",nperseg=nperseg,noverlap=noverlap,boundary=None,padded=False)
    psd=np.mean(np.abs(z)**2,axis=1)
    powers=[]
    for i,(lo,hi,name) in enumerate(BANDS):
        mask=(f>=lo)&(f<hi)
        powers.append(float(np.sum(psd[mask])))
        if progress: progress(int((i+1)/len(BANDS)*100))
    return np.asarray(powers,dtype=float)



def _dbfs_from_amplitude(amplitude: float) -> float:
    return float(20.0 * np.log10(max(float(amplitude), 1e-12)))


def global_peak_dbfs(x):
    """Sample peak over all channels, referenced to full-scale PCM (0 dBFS = 1.0)."""
    return _dbfs_from_amplitude(float(np.max(np.abs(x))))


def global_rms_dbfs(x):
    """RMS over all PCM samples/channels, referenced to full-scale PCM."""
    rms=float(np.sqrt(np.mean(np.square(np.asarray(x,dtype=np.float64)))))
    return _dbfs_from_amplitude(rms)


def global_true_peak_dbtp(x, oversample=4):
    """Estimate true peak using 4x polyphase oversampling per channel."""
    from scipy.signal import resample_poly
    arr=np.asarray(x,dtype=np.float64)
    if arr.ndim==1:
        arr=arr[:,None]
    peak=0.0
    for ch in range(arr.shape[1]):
        up=resample_poly(arr[:,ch], int(oversample), 1)
        if len(up):
            peak=max(peak,float(np.max(np.abs(up))))
    return _dbfs_from_amplitude(peak)


def global_crest_factor_db(x):
    """Crest factor = sample peak dBFS minus RMS dBFS."""
    return float(global_peak_dbfs(x)-global_rms_dbfs(x))

def global_integrated_lufs(x, sr):
    """Integrated loudness in LUFS using the ITU-R BS.1770 gated loudness algorithm."""
    arr=np.asarray(x,dtype=np.float64)
    if arr.ndim==1:
        arr=arr[:,None]
    if arr.size==0:
        return float("-inf")
    meter=pyln.Meter(int(sr))
    min_samples=int(np.ceil(meter.block_size*sr))
    if arr.shape[0] < min_samples:
        padded=np.zeros((min_samples,arr.shape[1]),dtype=np.float64)
        padded[:arr.shape[0]]=arr
        arr=padded
    return float(meter.integrated_loudness(arr))

def band_energy_metrics(x,sr,progress=None):
    """Compute normalized band levels and measured energy occupancy from one STFT."""
    powers=_band_power_values(x,sr,progress)
    values=10*np.log10(powers+1e-20)
    values-=np.mean(values)
    total=float(np.sum(powers))
    occupancy=(powers/total*100.0) if total>0.0 else np.zeros(len(BANDS),dtype=float)
    return values,occupancy


def band_energy_db(x,sr,progress=None):
    return band_energy_metrics(x,sr,progress)[0]


def _peaking_biquad_coeffs(sample_rate, frequency, gain_db, q):
    """RBJ peaking-EQ digital biquad coefficients."""
    A = 10.0 ** (float(gain_db) / 40.0)
    w0 = 2.0 * np.pi * float(frequency) / float(sample_rate)
    alpha = np.sin(w0) / (2.0 * max(float(q), 1e-9))
    cw = np.cos(w0)
    b0 = 1.0 + alpha * A
    b1 = -2.0 * cw
    b2 = 1.0 - alpha * A
    a0 = 1.0 + alpha / A
    a1 = -2.0 * cw
    a2 = 1.0 - alpha / A
    return (np.array([b0, b1, b2], dtype=float) / a0,
            np.array([1.0, a1 / a0, a2 / a0], dtype=float))


def _post_eq_band_powers(x, sr, eq_recommendations, progress=None):
    """Apply the proposed EQ as digital biquad frequency responses to the measured FFT spectrum."""
    mono=np.mean(x,axis=1)
    nperseg=min(65536,len(mono))
    if nperseg<1024: nperseg=len(mono)
    noverlap=int(nperseg*0.75) if nperseg>1 else 0
    f,_,z=stft(mono,fs=sr,window="hann",nperseg=nperseg,noverlap=noverlap,boundary=None,padded=False)
    psd=np.mean(np.abs(z)**2,axis=1)
    response=np.ones_like(f,dtype=float)
    valid=[]
    for rec in eq_recommendations or []:
        if getattr(rec,"filter_type","").lower() != "bell":
            continue
        b,a=_peaking_biquad_coeffs(sr,rec.frequency,rec.gain_db,rec.q)
        _,h=freqz(b,a,worN=2.0*np.pi*f/float(sr))
        mag=np.abs(h)
        response *= mag
        valid.append(rec)
    post_psd=psd*(response**2)
    powers=[]
    for i,(lo,hi,name) in enumerate(BANDS):
        mask=(f>=lo)&(f<hi)
        powers.append(float(np.sum(post_psd[mask])))
        if progress: progress(int((i+1)/len(BANDS)*100))
    return np.asarray(powers,dtype=float)


def band_energy_post_eq_occupancy_pct(x,sr,eq_recommendations):
    """Return Post % after applying every proposed Bell EQ to the FFT spectrum."""
    powers=_post_eq_band_powers(x,sr,eq_recommendations)
    total=float(np.sum(powers))
    if total<=0.0:
        return np.zeros(len(BANDS),dtype=float)
    return powers/total*100.0


def band_energy_occupancy_pct(x,sr):
    """Measured energy occupancy percentage for the active bands only.

    Each band's percentage is its measured linear spectral energy divided by
    the measured energy across all active bands. No target/reference data is
    used. The returned percentages sum to approximately 100.00%.
    """
    powers=_band_power_values(x,sr)
    total=float(np.sum(powers))
    if total<=0.0:
        return np.zeros(len(BANDS),dtype=float)
    return powers/total*100.0
