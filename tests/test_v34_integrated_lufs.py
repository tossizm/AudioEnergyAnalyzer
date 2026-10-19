from pathlib import Path
import numpy as np
import soundfile as sf
import pyloudnorm as pyln

ROOT=Path(__file__).parents[1]
PIPE=(ROOT/"app/analysis/pipeline.py").read_text(encoding="utf-8")
GUI=(ROOT/"app/gui/main_window.py").read_text(encoding="utf-8")
MODEL=(ROOT/"app/models/result.py").read_text(encoding="utf-8")
SPECTRUM=(ROOT/"app/analysis/spectrum.py").read_text(encoding="utf-8")

def test_integrated_lufs_field_and_display_order():
    assert "integrated_lufs" in MODEL
    keys='("Peak", "RMS", "TruePeak", "Integrated LUFS", "クレストファクター", "全体相関")'
    assert keys in GUI
    assert '"Integrated LUFS"' in GUI

def test_integrated_lufs_matches_pyloudnorm_reference(tmp_path):
    sr=48000
    t=np.arange(sr*2,dtype=np.float64)/sr
    x=(0.1*np.sin(2*np.pi*1000*t)).astype(np.float32)
    audio=tmp_path/"tone.wav"
    sf.write(audio,x,sr)
    from app.analysis.spectrum import global_integrated_lufs
    got=global_integrated_lufs(x,sr)
    ref=float(pyln.Meter(sr).integrated_loudness(x))
    assert np.isfinite(got)
    assert abs(got-ref)<1e-6

def test_integrated_lufs_saved_in_result_text():
    assert 'Integrated LUFS : {r.integrated_lufs:.2f} LUFS' in GUI

def test_analyze_file_populates_integrated_lufs(tmp_path):
    import json
    from app.analysis.pipeline import analyze_file
    sr=48000
    t=np.arange(sr*2,dtype=np.float64)/sr
    tone=(0.1*np.sin(2*np.pi*1000*t)).astype(np.float32)
    x=np.column_stack([tone,tone])
    audio=tmp_path/"stereo_tone.wav"
    sf.write(audio,x,sr)
    cfg=tmp_path/"target.json"
    cfg.write_text(json.dumps({"target_db":[0]*10,"tolerance_db":[2]*10,"priority_weight":[1]*10}),encoding="utf-8")
    r=analyze_file(audio,cfg)
    assert np.isfinite(r.integrated_lufs)
