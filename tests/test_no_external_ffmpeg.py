from pathlib import Path

def test_build_does_not_require_external_ffmpeg():
    text=Path("build_windows.bat").read_text(encoding="utf-8")
    assert "ffmpeg\\ffmpeg.exe" not in text
    assert "--collect-all av" in text

def test_mp3_loader_uses_pyav():
    text=Path("app/analysis/spectrum.py").read_text(encoding="utf-8")
    assert "import av" in text
    assert "_ffmpeg_path" not in text
