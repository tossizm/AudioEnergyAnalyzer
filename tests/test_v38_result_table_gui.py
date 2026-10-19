from pathlib import Path

GUI = Path(__file__).parents[1] / "app" / "gui" / "main_window.py"
TEXT = GUI.read_text(encoding="utf-8")


def test_result_table_has_target_percentage_and_requested_labels():
    assert 'QTableWidget(0,9)' in TEXT
    assert '["Band","Sample %","Target %","Correlation","Post %","Diff","Sample dB","Target dB","EQ"]' in TEXT
    assert 'self.table.setColumnHidden(4,True)' in TEXT
    assert 'self.table.setColumnHidden(5,True)' in TEXT
    assert 'self.table.setColumnHidden(8,True)' in TEXT


def test_result_table_uses_metric_row_base_font():
    assert 'self.table.setFont(self.metric_labels["Peak"].font())' in TEXT
    assert 'h.setFont(self.metric_labels["Peak"].font())' in TEXT


def test_sample_db_is_yellow_and_bold_and_target_pct_is_white():
    assert 'elif j==2:\n                    it.setForeground(QColor("#FFFFFF"))' in TEXT
    assert 'if j==6:\n                    ft=it.font(); ft.setBold(True); it.setFont(ft)\n                    it.setForeground(QColor("#FFD84D"))' in TEXT
