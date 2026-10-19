from pathlib import Path

ROOT = Path(__file__).parents[1]
GUI = (ROOT / "app" / "gui" / "main_window.py").read_text(encoding="utf-8")
MODEL = (ROOT / "app" / "models" / "result.py").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github" / "workflows" / "python-tests.yml").read_text(encoding="utf-8")


def test_selected_reference_is_saved_to_runtime_config_folder():
    assert 'config_dir=resource_path("config")' in GUI
    assert 'return config_dir/"selected_config.json"' in GUI
    assert 'cache.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\\n",encoding="utf-8")' in GUI


def test_analysis_elapsed_time_is_shown_and_exported():
    assert "analysis_elapsed_seconds" in MODEL
    assert "time.perf_counter()" in GUI
    assert "分析時間：" in GUI
    assert "Analysis Time :" in GUI


def test_result_table_alignment_matches_column_roles():
    assert "Qt.AlignLeft if j in (0,8) else Qt.AlignRight" in GUI


def test_artifact_zip_has_numbered_name_and_expected_root_folder():
    assert 'AudioEnergyAnalyzer-${{ github.run_number }}.zip' in WORKFLOW
    assert 'name: AudioEnergyAnalyzer-${{ github.run_number }}' in WORKFLOW
    assert 'Join-Path $PWD "package/AudioEnergyAnalyzer"' in WORKFLOW
    assert 'AudioEnergyAnalyzer/AudioEnergyAnalyzer.exe' in WORKFLOW
