from pathlib import Path
import json
import numpy as np
import soundfile as sf

ROOT = Path(__file__).parents[1]
GUI = (ROOT / 'app' / 'gui' / 'main_window.py').read_text(encoding='utf-8')
MAIN = (ROOT / 'app' / 'main.py').read_text(encoding='utf-8')
BAT = (ROOT / 'build_windows.bat').read_text(encoding='utf-8')
CLEAN = (ROOT / 'cleanup_after_build.bat').read_text(encoding='utf-8')


def test_external_runtime_resource_resolution_does_not_use_meipass():
    assert 'sys.executable' in MAIN
    assert 'sys._MEIPASS' not in MAIN
    assert 'exe_dir / relative' in MAIN
    assert 'exe_dir.parent / relative' in MAIN


def test_external_config_is_not_bundled_into_onefile():
    assert '--add-data "config;config"' not in BAT
    assert 'xcopy /E /I /Y "config\\*" "dist\\config\\"' in BAT


def test_cleanup_preserves_runtime_dirs():
    assert 'not "%%~nxD"=="dist"' in CLEAN
    assert 'not "%%~nxD"=="config"' in CLEAN
    assert 'not "%%~nxD"=="ffmpeg"' in CLEAN
    assert '%TEMP%\\_MEI*' in CLEAN


def test_result_has_pre_and_post_columns():
    assert '["Band","Pre %","Correlation","Post %","Diff","Sample","Target","EQ"]' in GUI
    assert 'b.post_energy_occupancy_pct' in GUI


def test_post_eq_energy_changes_for_nonzero_eq(tmp_path):
    from app.analysis.spectrum import band_energy_occupancy_pct, band_energy_post_eq_occupancy_pct, _band_power_values, _post_eq_band_powers, reset_bands
    from app.models.result import EQRecommendation
    sr = 48000
    t = np.arange(sr, dtype=np.float32) / sr
    x = np.column_stack([np.sin(2*np.pi*1000*t), np.sin(2*np.pi*1000*t)]).astype(np.float32)
    pre = band_energy_occupancy_pct(x, sr)
    post = band_energy_post_eq_occupancy_pct(x, sr, [EQRecommendation('Bell', 1000.0, 6.0, 1.0)])
    assert np.isclose(pre.sum(), 100.0, atol=1e-8)
    assert np.isclose(post.sum(), 100.0, atol=1e-8)
    raw_pre = _band_power_values(x, sr)
    raw_post = _post_eq_band_powers(x, sr, [EQRecommendation('Bell', 1000.0, 6.0, 1.0)])
    assert float(raw_post.sum()) > float(raw_pre.sum())
    reset_bands()


def test_band_settings_payload_preserves_custom_input_values():
    from app.analysis.spectrum import build_band_settings_payload
    maxima = [55, 111, 222, 444, 888, 1777, 3555, 7111, 15000]
    data = build_band_settings_payload(maxima)
    assert [b["min_hz"] for b in data["bands"]] == [20,55,111,222,444,888,1777,3555,7111,15000]
    assert [b["max_hz"] for b in data["bands"]] == maxima + [20000]


def test_post_energy_is_present_on_analysis_result(tmp_path):
    import json
    from app.analysis.pipeline import analyze_file
    import soundfile as sf
    sr=48000
    t=np.arange(sr,dtype=np.float32)/sr
    x=np.column_stack([0.3*np.sin(2*np.pi*100*t)+0.1*np.sin(2*np.pi*1000*t), 0.3*np.sin(2*np.pi*100*t)+0.1*np.sin(2*np.pi*1000*t)]).astype(np.float32)
    audio=tmp_path/"sample.wav"; sf.write(audio,x,sr)
    cfg=tmp_path/"target.json"; cfg.write_text(json.dumps({"target_db":[0]*10,"tolerance_db":[1.5]*10,"priority_weight":[1]*10}),encoding="utf-8")
    result=analyze_file(audio,cfg)
    assert len(result.bands)==10
    assert all(hasattr(b,"post_energy_occupancy_pct") for b in result.bands)
    assert np.isclose(sum(b.post_energy_occupancy_pct for b in result.bands),100.0,atol=0.05)


def test_v32_global_metrics_and_v36_wav_progress_stage():
    assert 'Peak",r.peak_dbfs,"dBFS"' in GUI
    assert 'TruePeak",r.true_peak_dbtp,"dBTP"' in GUI
    assert 'RMS",r.rms_dbfs,"dBFS"' in GUI
    assert 'クレストファクター",r.crest_factor_db,"dB"' in GUI
    assert '全体相関",r.stereo_correlation,"",3' in GUI
    assert 'Five global measurements are placed between the three action buttons and the result table.' in GUI
    assert 'if ext==".mp3":' in (ROOT / 'app' / 'analysis' / 'pipeline.py').read_text(encoding='utf-8')
    pipeline = (ROOT / 'app' / 'analysis' / 'pipeline.py').read_text(encoding='utf-8')
    assert 'emit("load",0)' in pipeline
    assert 'load_audio(path,lambda p:emit("load",p))' in pipeline
