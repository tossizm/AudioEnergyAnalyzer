# ClubAudioAnalyzer — Standalone Windows App

ClubAudioAnalyzer v38 baseline: a local Windows desktop application for analyzing audio samples against a 10-band reference JSON. This repository is for the **standalone Python application**; the separate `tossizm/ClubAudioAnalyzerEQ` repository is for the JUCE VST3 plug-in and should not be mixed into this source tree.

## Current source layout

- `app/` — GUI and analysis implementation.
- `app/analysis/spectrum.py` — STFT-based band energy measurement and occupancy calculation.
- `app/analysis/pipeline.py` — standard reference comparison and EQ suggestions.
- `app/analysis/ratio_targeting.py` — target energy-ratio EQ optimization.
- `app/gui/main_window.py` — PySide6 interface.
- `config/Reference_Average_Default.json` — default reference JSON.
- `tests/` — automated regression tests.
- `docs/approved_ui/` — approved UI reference images; use these as the visual acceptance baseline.
- `docs/verification/` — verification snapshots and notes.
- `build_windows.bat` — local Windows test and EXE build.
- `.github/workflows/python-tests.yml` — Windows CI tests on pushes and pull requests.

## Requirements

- Windows 10/11 (Windows 11 is the target environment)
- Python 3.11+
- Dependencies in `requirements.txt`

## Run locally

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
$env:QT_QPA_PLATFORM = "offscreen"
python -m pytest -q
python -m app.main
```

For a GUI session, `QT_QPA_PLATFORM=offscreen` is only needed for headless testing; remove it or open a new terminal before launching the GUI if the platform setting interferes with display.

## Build the Windows EXE

Double-click `build_windows.bat`. The script installs requirements, runs pytest, and creates `dist/ClubAudioAnalyzer.exe`; it also copies the `config` and `ffmpeg` folders when present. The app uses PyAV for in-process audio decoding. Do not commit `.venv/`, `build/`, `dist/`, `__pycache__/`, `.pytest_cache/`, or generated executables to the source repository.

## Analysis behavior notes

- Standard bands: 20–60, 60–120, 120–250, 250–500, 500–1000, 1000–2000, 2000–5000, 5000–10000, 10000–16000, 16000–20000 Hz. The UI supports customized band edges.
- Band occupancy is measured from linear spectral energy and normalized across the currently active bands; it is not read from the reference JSON.
- Standard comparison EQ and target-ratio optimization are separate paths. Do not conflate the proportional correction in `pipeline.py` with the iterative optimizer in `ratio_targeting.py`.
- Any algorithm change should include regression tests and before/after comparisons on the same audio fixtures. A passing unit test suite does not establish perceptual or club-system accuracy.

## Required validation before a release ZIP

1. Implement the change on a feature branch.
2. Run `python -m pytest -q` and verify GitHub Actions is green.
3. Build the EXE on Windows and launch it.
4. Inspect every affected GUI screen against `docs/approved_ui/` and the latest user-approved screenshots.
5. Test the relevant workflows end-to-end (audio drag/drop, JSON loading, analysis, EQ output, result generation, band customization, return-to-start prompt, and persistence as applicable).
6. Fix mismatches and repeat steps 2–5 before packaging.
7. Record what was tested and what remains unverified in the PR description/release notes.

## GitHub workflow

Use a separate repository named `ClubAudioAnalyzer` for this standalone project. Create a branch for each change, commit focused changes, and open a pull request into `main`. Do not merge until CI passes and the Windows GUI validation above is complete. The included Actions workflow runs Python tests; it does **not** prove that the packaged EXE works or replace visual/DAW/manual testing.

## Security and files

Never commit access tokens, credentials, private audio, user-specific data, or unrelated build outputs. GitHub's browser upload is limited to 25 MiB per file; use Git/GitHub Desktop for a structured source project or files beyond browser limits.
