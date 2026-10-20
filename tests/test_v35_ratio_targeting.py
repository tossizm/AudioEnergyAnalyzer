from pathlib import Path
import json
import numpy as np
import soundfile as sf

ROOT = Path(__file__).parents[1]
GUI = (ROOT / "app" / "gui" / "main_window.py").read_text(encoding="utf-8")
RATIO = (ROOT / "app" / "analysis" / "ratio_targeting.py").read_text(encoding="utf-8")
PIPE = (ROOT / "app" / "analysis" / "pipeline.py").read_text(encoding="utf-8")


def test_ratio_targeting_is_separate_from_existing_target_db_algorithm():
    optimize_part = RATIO[RATIO.index('def optimize_ratio_eq'): ]
    assert 'validate_ratio_target(target_pct)' in optimize_part
    assert 'target[\"target_db\"]' not in optimize_part
    assert 'priority_weight' not in optimize_part
    assert 'target_db' in PIPE
    assert 'diff[i]' in PIPE
    assert '_eq_for_band' in PIPE
    assert '10.0 * np.log10(target_math / safe_pre)' in RATIO
    assert 'np.linalg.lstsq' in RATIO


def test_ratio_target_allows_zero_only_for_band10_and_requires_sum_100():
    from app.analysis.ratio_targeting import validate_ratio_target
    ok = validate_ratio_target([10.0] * 10)
    assert len(ok) == 10 and np.isclose(np.sum(ok), 100.0)
    band10_zero = validate_ratio_target([100.0 / 9.0] * 9 + [0.0])
    assert band10_zero[-1] == 0.0 and np.isclose(np.sum(band10_zero), 100.0)
    try:
        validate_ratio_target([10.0] * 9 + [9.0])
    except ValueError:
        pass
    else:
        raise AssertionError("sum != 100 must be rejected")
    try:
        validate_ratio_target([0.0] + [100.0 / 9.0] * 9)
    except ValueError:
        pass
    else:
        raise AssertionError("zero in BAND1 must be rejected")


def test_ratio_optimizer_matches_target_without_using_target_db(tmp_path):
    from app.analysis.spectrum import BANDS, band_energy_occupancy_pct, reset_bands, set_band_maxima
    from app.analysis.ratio_targeting import optimize_ratio_eq

    set_band_maxima([60, 120, 250, 500, 1000, 2000, 5000, 10000, 16000])
    sr = 48000
    t = np.arange(sr * 4, dtype=float) / sr
    freqs = [35, 80, 170, 350, 707, 1414, 3162, 7071, 12649, 17889]
    amps = np.sqrt(np.array([0.12, 0.15, 0.14, 0.12, 0.10, 0.09, 0.08, 0.07, 0.08, 0.05]))
    x = np.zeros_like(t)
    for i, (amp, freq) in enumerate(zip(amps, freqs)):
        x += amp * np.sin(2 * np.pi * freq * t + 0.13 * i)
    stereo = np.column_stack([x, x]).astype(np.float32)

    pre = band_energy_occupancy_pct(stereo, sr)
    target = pre.copy()
    target[0] *= 1.15
    target[7] *= 0.80
    target[4] *= 0.95
    target = target / target.sum() * 100.0

    result = optimize_ratio_eq(stereo, sr, target, max_iterations=8, tolerance_pct=0.05)
    assert len(result.eq_gains_db) == 10
    assert np.isclose(float(result.post_pct.sum()), 100.0, atol=1e-8)
    assert result.max_abs_error_pct < 0.05
    assert np.allclose(result.eq_gains_db, np.round(result.eq_gains_db, 2))
    assert result.converged
    assert np.max(np.abs(result.pre_pct - target)) > 0.5
    reset_bands()


def test_ratio_eq_gui_entry_points_and_export_section():
    assert '比率リファレンス設定' in GUI
    assert '目標比率へEQ調整' in GUI
    assert 'class RatioReferencePage' in GUI
    assert 'class RatioEQDialog' in GUI
    assert 'def start_ratio_eq' in GUI
    assert 'RATIO TARGET EQ' in GUI
    assert 'ratio_target_percent' in GUI
    assert 'self.resize(980,620)' in GUI


def test_ratio_reference_gui_allows_zero_only_for_band10():
    assert "i < 9 and v == 0.0" in GUI


def test_ratio_percent_to_db_round_trip_preserves_selected_reference_baseline():
    from app.analysis.ratio_targeting import default_ratio_from_target_db, target_db_from_ratio
    reference = np.array([5.0, 7.5, 3.75, 3.0, 2.5, 2.0, 1.25, -0.25, -1.0, -23.75])
    pct = default_ratio_from_target_db(reference)
    recovered = target_db_from_ratio(pct, reference)
    assert np.allclose(recovered, reference, atol=1e-10)
    changed = pct.copy()
    changed[0] *= 1.2
    changed[1] *= 0.8
    changed = changed / changed.sum() * 100.0
    converted = target_db_from_ratio(changed, reference)
    assert np.isclose(np.mean(converted), np.mean(reference), atol=1e-10)
    assert np.allclose(default_ratio_from_target_db(converted), changed, atol=1e-8)


def test_ratio_page_uses_active_reference_and_saves_target_db():
    assert 'default_ratio_from_target_db(data.get("target_db",[]))' in GUI
    assert 'target_db_from_ratio(vals, data.get("target_db",[]))' in GUI
    assert 'config_path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\\n",encoding="utf-8")' in GUI
    assert 'def _current_ratio_target(self):' in GUI
