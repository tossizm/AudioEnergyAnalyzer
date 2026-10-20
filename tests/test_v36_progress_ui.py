from pathlib import Path
import re

ROOT = Path(__file__).parents[1]
GUI = (ROOT / "app" / "gui" / "main_window.py").read_text(encoding="utf-8")
MAIN = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
SPECTRUM = (ROOT / "app" / "analysis" / "spectrum.py").read_text(encoding="utf-8")
PIPE = (ROOT / "app" / "analysis" / "pipeline.py").read_text(encoding="utf-8")


def test_progress_view_is_graphic_only_and_uses_mmss_elapsed_time():
    assert "QProgressBar" in GUI
    assert "setTextVisible(False)" in GUI
    assert "QProgressBar{background:transparent;border:2px solid #000000" in GUI
    assert "QProgressBar::chunk{background:#ED1A3D" in GUI
    assert "経過時間：00:00" in GUI
    assert "経過時間：{self._mmss(self._timer.elapsed())}" in GUI
    assert re.search(r'def _mmss\(ms\):', GUI)


def test_normal_audio_progress_combines_load_and_analysis_to_single_0_100_bar():
    assert 'overall=int(float(pct)*0.30)' in GUI
    assert 'overall=30+int(float(pct)*0.70)' in GUI
    assert 'self.progress_page.start(start_text)' in GUI
    assert 'self.progress_page.update(text,overall)' in GUI
    assert '：{pct} %' not in GUI


def test_wav_aiff_loading_reports_fine_grained_progress():
    assert 'emit("load",0)' in PIPE
    assert 'load_audio(path,lambda p:emit("load",p))' in PIPE
    assert 'block=65536' in SPECTRUM


def test_main_window_is_resizable_while_preserving_initial_size():
    assert 'self.resize(1100,550)' in GUI
    assert 'self.setMinimumSize(700,400)' in GUI
    assert 'self.setFixedSize(1100,550)' not in GUI


def test_startup_popup_is_shown_until_main_gui_is_visible():
    assert '[プログラムを起動しています]' in MAIN
    assert 'startup_popup = _show_startup_popup(app)' in MAIN
    assert 'from app.gui.main_window import MainWindow' in MAIN
    assert 'win.show()' in MAIN
    assert 'startup_popup.close()' in MAIN
    assert 'QDialog' in MAIN and 'QLabel' in MAIN
