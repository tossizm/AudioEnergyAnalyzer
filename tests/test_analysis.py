import json
import numpy as np
from app.analysis.stereo import correlation

def test_identical_stereo_is_one():
    x = np.random.default_rng(0).normal(size=10000)
    assert abs(correlation(np.column_stack([x,x])) - 1.0) < 1e-9

def test_inverted_stereo_is_minus_one():
    x = np.random.default_rng(1).normal(size=10000)
    assert abs(correlation(np.column_stack([x,-x])) + 1.0) < 1e-9


def test_band_energy_occupancy_is_measured_only_and_sums_to_100_percent():
    from app.analysis.spectrum import band_energy_occupancy_pct, reset_bands
    sr = 48000
    t = np.arange(sr, dtype=float) / sr
    x = np.column_stack([np.sin(2 * np.pi * 750 * t), np.sin(2 * np.pi * 750 * t)])
    pct = band_energy_occupancy_pct(x, sr)
    assert len(pct) == 10
    assert np.isclose(float(np.sum(pct)), 100.0, atol=1e-8)
    # 750 Hz belongs to the 500-1000 Hz band in the active 10-band definition.
    assert int(np.argmax(pct)) == 4
    assert pct[4] > 99.0
    reset_bands()


def test_global_audio_metrics_units_and_values():
    from app.analysis.spectrum import global_peak_dbfs, global_true_peak_dbtp, global_rms_dbfs, global_crest_factor_db
    sr=48000
    t=np.arange(sr,dtype=np.float64)/sr
    x=np.column_stack([0.5*np.sin(2*np.pi*1000*t),0.5*np.sin(2*np.pi*1000*t)])
    peak=global_peak_dbfs(x)
    rms=global_rms_dbfs(x)
    true_peak=global_true_peak_dbtp(x)
    crest=global_crest_factor_db(x)
    assert -6.1 < peak < -5.9
    assert -9.2 < rms < -9.0
    assert true_peak >= peak - 1e-6
    assert 3.0 < crest < 3.2


def test_wav_analysis_skips_decode_stage(monkeypatch, tmp_path):
    from app.analysis.pipeline import analyze_file
    import soundfile as sf
    sr=48000
    t=np.arange(sr,dtype=np.float32)/sr
    x=np.column_stack([0.2*np.sin(2*np.pi*100*t),0.2*np.sin(2*np.pi*100*t)]).astype(np.float32)
    audio=tmp_path/'sample.wav'; sf.write(audio,x,sr)
    cfg=tmp_path/'target.json'; cfg.write_text(json.dumps({'target_db':[0]*10,'tolerance_db':[1.5]*10,'priority_weight':[1]*10}),encoding='utf-8')
    stages=[]
    analyze_file(audio,cfg,lambda stage,pct: stages.append(stage))
    assert 'decode' not in stages
    assert 'analysis' in stages
