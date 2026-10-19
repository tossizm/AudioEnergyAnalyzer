import sys
import shutil
import subprocess
import urllib.request
import zipfile
from pathlib import Path
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QVBoxLayout, QMessageBox
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
    popup.startup_label = label
    layout.addWidget(label)
    popup.show()
    app.processEvents()
    return popup



def ensure_ffmpeg(app, startup_popup):
    """Download a Windows essentials build linked from FFmpeg official download page if missing."""
    ffmpeg_dir = resource_path("ffmpeg")
    ffmpeg_dir.mkdir(parents=True, exist_ok=True)
    executable = ffmpeg_dir / "ffmpeg.exe"
    if executable.is_file() and executable.stat().st_size > 0:
        return True

    archive_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    archive_path = ffmpeg_dir / "ffmpeg-release-essentials.zip"
    try:
        if hasattr(startup_popup, 'startup_label'):
            startup_popup.startup_label.setText('[ffmpeg.exeをダウンロードしています]')
            app.processEvents()
        request = urllib.request.Request(archive_url, headers={"User-Agent": "AudioEnergyAnalyzer/1.0"})
        with urllib.request.urlopen(request, timeout=60) as response, open(archive_path, "wb") as output:
            shutil.copyfileobj(response, output)

        with zipfile.ZipFile(archive_path, "r") as archive:
            member = next((name for name in archive.namelist()
                           if name.replace("\\", "/").lower().endswith("/bin/ffmpeg.exe")), None)
            if member is None:
                raise RuntimeError("ダウンロードしたアーカイブに bin/ffmpeg.exe がありません。")
            with archive.open(member) as source, open(executable, "wb") as destination:
                shutil.copyfileobj(source, destination)

        check = subprocess.run([str(executable), '-version'], stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, timeout=15, check=False,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if check.returncode != 0:
            executable.unlink(missing_ok=True)
            raise RuntimeError("ダウンロードした ffmpeg.exe の起動確認に失敗しました。")
        return True
    except Exception as exc:
        executable.unlink(missing_ok=True)
        QMessageBox.warning(startup_popup, "FFmpeg ダウンロード失敗",
                            "ffmpeg.exe を自動取得できませんでした。ネットワーク接続を確認してください。\n"
                            f"詳細：{exc}")
        return False
    finally:
        archive_path.unlink(missing_ok=True)

def main():
    app = QApplication(sys.argv)
    startup_popup = _show_startup_popup(app)
    app.processEvents()
    ensure_ffmpeg(app, startup_popup)
    startup_popup.startup_label.setText('[プログラムを起動しています]')
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
