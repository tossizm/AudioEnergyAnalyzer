from pathlib import Path

GUI = Path(__file__).parents[1] / "app" / "gui" / "main_window.py"
TEXT = GUI.read_text(encoding="utf-8")


def test_result_table_eq_column_is_last():
    assert '["Band","Pre %","Correlation","Post %","Diff","Sample","Target","EQ"]' in TEXT


def test_result_table_uses_metric_row_base_font():
    assert 'self.table.setFont(self.metric_labels["Peak"].font())' in TEXT
    assert 'h.setFont(self.metric_labels["Peak"].font())' in TEXT


def test_pre_and_correlation_values_are_yellow_and_eq_is_not_bold():
    assert 'if j in (1,2):\n                    it.setForeground(QColor("#FFD84D"))' in TEXT
    assert 'if j in (1,2,3,4):' in TEXT
    assert 'if j==7:' not in TEXT
    assert 'eq_text,f"{b.diff_db' not in TEXT
