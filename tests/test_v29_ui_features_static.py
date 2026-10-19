from pathlib import Path

ROOT = Path(__file__).parents[1]
GUI = (ROOT / 'app' / 'gui' / 'main_window.py').read_text(encoding='utf-8')
PIPE = (ROOT / 'app' / 'analysis' / 'pipeline.py').read_text(encoding='utf-8')


def test_startup_has_both_required_buttons_and_no_home_button():
    assert 'self.set_genre_button=QPushButton("リファレンスデータ設定", self)' in GUI
    assert 'self.band_button=QPushButton("帯域カスタマイズ", self)' in GUI
    assert 'self.drop.home_button' not in GUI
    assert 'pad=40' in GUI
    assert 'self.applied.setGeometry(pad,350,w-pad*2,80)' in GUI


def test_global_font_scaling_is_110_percent_of_previous_sizes():
    assert 'base.setPointSizeF(base_size*1.32)' in GUI
    assert 'startup_size=base_size*1.76' in GUI


def test_band_settings_persistence_controls_exist():
    for text in ('設定を保存','設定を適用','デフォルトに戻す'):
        assert f'QPushButton("{text}"' in GUI
    assert 'maxima=[int(edit.text().strip()) for edit in self.inputs]' in GUI
    assert 'return build_band_settings_payload(maxima)' in GUI
    assert 'self._restore_default' in GUI


def test_band_layout_has_40px_top_gap_and_bottom_margin_and_red_decision_button():
    assert 'self.title.setGeometry(0,0,w,33)' in GUI
    assert 'y0=73' in GUI
    assert 'status_y=392' in GUI
    assert 'button_y=550-40-42' in GUI
    assert 'background:#ED1A3D;color:#FFFFFF' in GUI


def test_result_hides_status_priority_and_renames_energy_column():
    assert 'QTableWidget(0,9)' in GUI
    assert '["Band","Sample %","Target %","Correlation","Post %","Diff","Sample dB","Target dB","EQ"]' in GUI
    assert 'self.table.setColumnHidden(4,True)' in GUI
    assert 'self.table.setColumnHidden(5,True)' in GUI
    assert 'self.table.setColumnHidden(8,True)' in GUI
    assert 'b.status' not in GUI[GUI.index('def show_result'):GUI.index('def save_result')]
    assert 'priority_display' not in GUI[GUI.index('def show_result'):GUI.index('def save_result')]


def test_eq_is_generated_for_any_nonzero_diff():
    assert 'if diff == 0.0:return None' in PIPE
    assert 'if abs(diff)<1.0:return None' not in PIPE
