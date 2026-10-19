from pathlib import Path


def test_band_rows_are_centered_without_sequence_labels():
    src = Path(__file__).parents[1] / 'app' / 'gui' / 'main_window.py'
    text = src.read_text(encoding='utf-8')
    # Sequence labels ①～⑩ are intentionally not rendered in the UI.
    assert 'row_label' not in text
    assert 'shift=42' not in text
    assert 'self._shift_row_labels' not in text
    # The row is positioned as one centered "xx Hz ～ xx Hz" unit.
    assert 'total=min_w+gap_num_hz+unit_w+gap_hz_tilde+tilde_w+gap_tilde_box+box_w+gap_box_hz+unit_w' in text
    assert 'x0=int((w-total)/2)' in text
    # Two full-width characters separate the first Hz and tilde.
    assert 'gap_hz_tilde=2*fw' in text
    # Editable boxes remain 126 px wide (the approved 75% width).
    assert 'box_w=126' in text


def test_result_table_has_measured_energy_occupancy_column():
    src = Path(__file__).parents[1] / 'app' / 'gui' / 'main_window.py'
    text = src.read_text(encoding='utf-8')
    assert 'QTableWidget(0,9)' in text
    assert '["Band","Sample %","Target %","Correlation","Post %","Diff","Sample dB","Target dB","EQ"]' in text
    assert 'self.table.setColumnHidden(4,True)' in text
    assert 'self.table.setColumnHidden(5,True)' in text
    assert 'self.table.setColumnHidden(8,True)' in text
    assert 'f"{b.energy_occupancy_pct:.2f} %"' in text


def test_build_script_cleans_only_unused_mei_directories():
    src = Path(__file__).parents[1] / 'build_windows.bat'
    text = src.read_text(encoding='utf-8')
    assert r'for /d %%D in ("%TEMP%\_MEI*")' in text
    assert 'rmdir /s /q "%%~fD"' in text
    assert 'if exist "%%~fD"' in text
