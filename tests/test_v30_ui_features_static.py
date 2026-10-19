from pathlib import Path

ROOT = Path(__file__).parents[1]
GUI = (ROOT / 'app' / 'gui' / 'main_window.py').read_text(encoding='utf-8')


def test_font_scale_is_110_percent_of_v29():
    assert 'base.setPointSizeF(base_size*1.32)' in GUI
    assert 'startup_size=base_size*1.76' in GUI


def test_band_save_uses_current_input_values_not_global_defaults():
    assert 'maxima=[int(edit.text().strip()) for edit in self.inputs]' in GUI
    assert 'from app.analysis.spectrum import build_band_settings_payload' in GUI
    assert 'return build_band_settings_payload(maxima)' in GUI


def test_band_settings_buttons_moved_up_40px():
    assert 'sx=w-margin-190; sy=195; bw=190; bh=42; gap=12' in GUI


def test_band_input_style_is_black_white_border_yellow_text():
    assert 'background:#000000;color:#FFFF00' in GUI
    assert 'border:1px solid #FFFFFF' in GUI


def test_analysis_navigation_prompt_and_save_task():
    assert '移動すると分析結果が失われます。分析データを保存しますか？' in GUI
    assert 'yes=box.addButton("YES(Y)", QMessageBox.YesRole)' in GUI
    assert 'no=box.addButton("NO(N)", QMessageBox.NoRole)' in GUI
    assert 'shortcut_y=QShortcut("Y", box)' in GUI
    assert 'shortcut_n=QShortcut("N", box)' in GUI
    assert 'if not self.save_result():' in GUI
    assert 'def save_result(self):' in GUI
    assert 'if self.current_result is None:return False' in GUI
    assert 'return True' in GUI[GUI.index('def save_result'):]


def test_decision_button_is_right_aligned_red_white():
    assert 'self.apply_button.setGeometry(w-margin-308,button_y,308,42)' in GUI
    assert 'background:#ED1A3D;color:#FFFFFF' in GUI
