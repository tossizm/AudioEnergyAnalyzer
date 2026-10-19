import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QVBoxLayout
from PySide6.QtCore import Qt
from app.gui.main_window import MainWindow
def resource_path(relative: str) -> Path:
    """Resolve external runtime resources beside the EXE, never from _MEIPASS.

    For a frozen PyInstaller build, the preferred location is EXE_DIR/<relative>.
    A parent-level fallback supports a project layout with dist/*.exe
    alongside config and ffmpeg folders.
    """
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        direct = exe_dir / relative
        if direct.exists():
            return direct
        parent = exe_dir.parent / relative
        if parent.exists():
            return parent
        return direct
    base = Path(__file__).resolve().parent.parent
    return base / relative

def _show_startup_popup(app):
    popup=QDialog()
    popup.setWindowTitle("AudioEnergyAnalyzer")
    popup.setModal(False)
    popup.setFixedSize(360,120)
    layout=QVBoxLayout(popup)
    label=QLabel("[プログラムを起動しています]")
    label.setAlignment(Qt.AlignCenter)
    layout.addWidget(label)
    popup.show()
    app.processEvents()
    return popup


def main():
    app = QApplication(sys.argv)
    startup_popup = _show_startup_popup(app)
    app.processEvents()
    win = MainWindow()
    win.show()
    app.processEvents()
    startup_popup.close()
    startup_popup.deleteLater()

    # File-drop handling belongs to MainWindow.start_analysis().
    # Do not connect the removed MainWindow.file_dropped signal here.
    for arg in sys.argv[1:]:
        path = Path(arg)
        if path.is_file() and path.suffix.lower() in {".mp3", ".wav", ".aif", ".aiff"}:
            win.start_analysis(str(path))
            break

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
