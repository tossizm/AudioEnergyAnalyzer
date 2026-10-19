def test_mainwindow_does_not_require_file_dropped_signal():
    # Regression guard: main.py must not reference the removed
    # MainWindow.file_dropped signal.
    from pathlib import Path
    text=Path("app/main.py").read_text(encoding="utf-8")
    assert "win.file_dropped.connect" not in text
