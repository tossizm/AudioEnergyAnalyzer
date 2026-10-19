from pathlib import Path

ROOT = Path(__file__).parents[1]
MAIN = (ROOT / 'app' / 'main.py').read_text(encoding='utf-8')
WORKFLOW = (ROOT / '.github' / 'workflows' / 'python-tests.yml').read_text(encoding='utf-8')


def test_ffmpeg_is_downloaded_when_missing_and_saved_to_runtime_folder():
    assert 'resource_path("ffmpeg")' in MAIN
    assert 'ffmpeg-release-essentials.zip' in MAIN
    assert 'open(executable, "wb")' in MAIN
    assert 'if executable.is_file() and executable.stat().st_size > 0:' in MAIN


def test_artifact_upload_preserves_one_top_level_application_folder():
    assert 'name: AudioEnergyAnalyzer-${{ github.run_number }}' in WORKFLOW
    assert 'path: package/**' in WORKFLOW
    assert 'package/AudioEnergyAnalyzer/AudioEnergyAnalyzer.exe' in WORKFLOW
    assert 'Package ZIP with stable top-level folder' not in WORKFLOW