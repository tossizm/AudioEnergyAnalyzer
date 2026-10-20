from pathlib import Path

ROOT = Path(__file__).parents[1]
MAIN = (ROOT / 'app' / 'main.py').read_text(encoding='utf-8')
WORKFLOW = (ROOT / '.github' / 'workflows' / 'python-tests.yml').read_text(encoding='utf-8')


def test_ffmpeg_is_downloaded_when_missing_and_saved_to_runtime_folder():
    assert 'resource_path("ffmpeg")' in MAIN
    assert 'ffmpeg-release-essentials.zip' in MAIN
    assert 'open(executable, "wb")' in MAIN
    assert 'if executable.is_file() and executable.stat().st_size > 0:' in MAIN


def test_artifact_uploads_one_root_folder_without_nested_zip():
    assert 'name: AudioEnergyAnalyzer-${{ github.run_number }}' in WORKFLOW
    assert 'path: package/' in WORKFLOW
    assert 'package/AudioEnergyAnalyzer/AudioEnergyAnalyzer.exe' in WORKFLOW
    assert 'Compress-Archive' not in WORKFLOW
    assert 'Verify single-root package folder without nested ZIP' in WORKFLOW
    assert 'AudioEnergyAnalyzer/AudioEnergyAnalyzer.exe' in WORKFLOW
    assert 'Nested ZIP files are forbidden in the package.' in WORKFLOW
    assert 'without wrapping a ZIP inside another ZIP' in WORKFLOW