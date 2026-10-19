from pathlib import Path


def test_pyinstaller_explicitly_collects_gui_module():
    script = Path("build_windows.bat").read_text(encoding="utf-8")
    assert "--collect-submodules app" in script
    assert "--hidden-import app.gui.main_window" in script


def test_gui_entry_module_exists():
    assert Path("app/gui/main_window.py").is_file()
    assert Path("app/gui/__init__.py").is_file()
