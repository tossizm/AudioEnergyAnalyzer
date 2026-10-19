from pathlib import Path
import json
import numpy as np
import soundfile as sf

ROOT=Path(__file__).parents[1]
GUI=(ROOT/"app/gui/main_window.py").read_text(encoding="utf-8")
PIPE=(ROOT/"app/analysis/pipeline.py").read_text(encoding="utf-8")
ST=(ROOT/"app/analysis/stereo.py").read_text(encoding="utf-8")

def test_only_default_reference_json_is_bundled():
    files=list((ROOT/"config").glob("*.json"))
    assert [p.name for p in files] == ["Reference_Average_Default.json"]
    data=json.loads(files[0].read_text(encoding="utf-8"))
    assert len(data["target_db"]) == 10

def test_first_launch_uses_default_reference():
    assert 'config/Reference_Average_Default.json' in GUI
    assert 'initial_reference_loaded' in GUI

def test_correlation_column_and_creation_time_are_saved():
    assert '["Band","Pre %","Correlation","Post %","Diff","Sample","Target","EQ"]' in GUI
    assert 'r.band_correlations' in GUI
    assert 'audio_created_at' in GUI
    assert 'Created :' in GUI

def test_metric_numeric_values_are_red_and_larger():
    assert 'color:#ED1A3D;font-size:150%;font-weight:700' in GUI

def test_band_correlations_are_computed():
    assert 'band_correlations(x,sr,BANDS)' in PIPE
    assert 'butter(4' in ST
    assert 'band_correlations' in ST

def test_band_correlation_values_are_real_numbers(tmp_path):
    from app.analysis.stereo import band_correlations
    from app.analysis.spectrum import BANDS
    sr=48000
    t=np.arange(sr,dtype=np.float32)/sr
    l=np.sin(2*np.pi*100*t)
    r=0.7*l + 0.3*np.sin(2*np.pi*350*t+0.4)
    x=np.column_stack([l,r]).astype(np.float32)
    vals=band_correlations(x,sr,BANDS)
    assert len(vals)==10
    assert all(np.isfinite(v) and -1.000001 <= v <= 1.000001 for v in vals)

def test_analysis_result_contains_band_correlations_and_created_at(tmp_path):
    from app.analysis.pipeline import analyze_file
    sr=48000
    t=np.arange(sr,dtype=np.float32)/sr
    x=np.column_stack([0.2*np.sin(2*np.pi*100*t),0.2*np.sin(2*np.pi*100*t)]).astype(np.float32)
    audio=tmp_path/"sample.wav"; sf.write(audio,x,sr)
    cfg=tmp_path/"target.json"; cfg.write_text(json.dumps({"target_db":[0]*10,"tolerance_db":[1.5]*10,"priority_weight":[1]*10}),encoding="utf-8")
    r=analyze_file(audio,cfg)
    assert len(r.band_correlations)==10
    assert r.audio_created_at
    assert all(np.isfinite(v) for v in r.band_correlations)
