import json
from pathlib import Path

import numpy as np
import soundfile as sf

from app.analysis.pipeline import generate_reference_config


def test_reference_config_matches_target_json_shape(tmp_path):
    sr = 48000
    t = np.arange(sr, dtype=np.float32) / sr
    x = np.column_stack([
        0.2 * np.sin(2 * np.pi * 100 * t) + 0.1 * np.sin(2 * np.pi * 1000 * t),
        0.2 * np.sin(2 * np.pi * 100 * t) + 0.1 * np.sin(2 * np.pi * 1000 * t),
    ]).astype(np.float32)
    audio = tmp_path / "reference.wav"
    sf.write(audio, x, sr)
    source = tmp_path / "target.json"
    source.write_text(json.dumps({
        "version": "0.1",
        "target_db": [0.0] * 10,
        "tolerance_db": [1.5] * 10,
        "priority_weight": [1.0] * 10,
        "name": "Test",
        "bpm": 150,
        "genre": "HardTechno",
        "notes": "test"
    }), encoding="utf-8")

    data = generate_reference_config(audio, source)

    assert list(data) == [
        "version", "target_db", "tolerance_db", "priority_weight",
        "name", "bpm", "genre", "notes"
    ]
    assert len(data["target_db"]) == 10
    assert data["tolerance_db"] == [1.5] * 10
    assert data["priority_weight"] == [1.0] * 10
    assert data["bpm"] == 150
    assert data["genre"] == "HardTechno"
    assert audio.name in data["notes"]
