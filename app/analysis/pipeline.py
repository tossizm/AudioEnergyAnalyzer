import json
import numpy as np
from datetime import datetime
from pathlib import Path
from app.models.result import AnalysisResult, BandResult, EQRecommendation
from app.analysis.spectrum import load_audio, band_energy_metrics, band_energy_post_eq_occupancy_pct, global_peak_dbfs, global_true_peak_dbtp, global_rms_dbfs, global_integrated_lufs, global_crest_factor_db, BANDS
from app.analysis.stereo import correlation, low_band_correlation, band_correlations

def _status(diff,tol):
    if diff>tol:return "OVER"
    if diff<-tol:return "UNDER"
    return "OK"

def _priority(diff,weight):
    a=abs(diff)*weight
    if a>=3:return "HIGH"
    if a>=1.5:return "MEDIUM"
    return "LOW"

def _eq_for_band(lo,hi,diff):
    if diff == 0.0:return None
    gain=float(np.clip(-diff*0.65,-4.0,4.0))
    freq=np.sqrt(lo*hi)
    q=float(np.clip(freq/(hi-lo),0.45,2.0))
    return EQRecommendation("Bell",round(float(freq),1),round(gain,1),round(q,2))

def analyze_file(path:Path,target_path:Path,progress=None):
    def emit(stage,pct):
        if progress: progress(stage,max(0,min(100,int(pct))))
    ext=path.suffix.lower()
    if ext==".mp3":
        emit("decode",0)
        x,sr=load_audio(path,lambda p:emit("decode",p))
    else:
        # WAV/AIFF are read progressively so the user can see input-processing progress.
        emit("load",0)
        x,sr=load_audio(path,lambda p:emit("load",p))
    emit("analysis",5)
    target=json.loads(target_path.read_text(encoding="utf-8"))
    emit("analysis",10)
    sample,occupancy=band_energy_metrics(x,sr,lambda p:emit("analysis",10+int(p*0.40)))
    emit("analysis",50)
    target_db=np.asarray(target["target_db"],dtype=float)
    if len(target_db)!=len(BANDS):raise ValueError("Target must contain exactly 10 values.")
    tol=np.asarray(target.get("tolerance_db",[1.5]*10),dtype=float)
    weights=np.asarray(target.get("priority_weight",[1.0]*10),dtype=float)
    diff=sample-target_db
    emit("analysis",70)
    bands=[]; eq=[]
    for i,(lo,hi,name) in enumerate(BANDS):
        rec=_eq_for_band(lo,hi,diff[i])
        if rec:eq.append(rec)
    post_occupancy=band_energy_post_eq_occupancy_pct(x,sr,eq)
    for i,(lo,hi,name) in enumerate(BANDS):
        b=BandResult(name,lo,hi,round(float(occupancy[i]),2),round(float(post_occupancy[i]),2),round(float(sample[i]),2),round(float(target_db[i]),2),round(float(diff[i]),2),_status(diff[i],tol[i]),_priority(diff[i],weights[i]))
        bands.append(b)
    emit("analysis",82)
    corr=correlation(x); emit("analysis",88)
    lowcorr=low_band_correlation(x,sr,120); emit("analysis",91)
    band_corrs=band_correlations(x,sr,BANDS); emit("analysis",94)
    peak_dbfs=global_peak_dbfs(x)
    true_peak_dbtp=global_true_peak_dbtp(x)
    rms_dbfs=global_rms_dbfs(x)
    integrated_lufs=global_integrated_lufs(x,sr)
    crest_db=global_crest_factor_db(x)
    emit("analysis",98)
    try:
        audio_created_at=datetime.fromtimestamp(path.stat().st_ctime).astimezone().isoformat(timespec="seconds")
    except Exception:
        audio_created_at=""
    bass_hz=120 if lowcorr>=0.7 else 250 if lowcorr>=0.5 else 60
    overall=f"Stereo Correlation {corr:+.2f}。低域相関 {lowcorr:+.2f}。"
    emit("analysis",100)
    return AnalysisResult(path.name,sr,len(x)/sr,corr,bass_hz,bands,eq,overall,peak_dbfs,true_peak_dbtp,rms_dbfs,integrated_lufs,crest_db,band_corrs,audio_created_at)


def generate_reference_config(path: Path, source_config_path: Path, progress=None):
    """Analyze an audio file as a reference and return a target-JSON-compatible dict.

    The measured 10-band balance becomes target_db. Judgment parameters
    (tolerance_db / priority_weight) and genre/BPM metadata are inherited from
    the currently selected config so the generated file can be used directly
    by the normal analysis pipeline.
    """
    def emit(stage, pct):
        if progress:
            progress(stage, max(0, min(100, int(pct))))

    emit("decode", 0)
    x, sr = load_audio(path, lambda p: emit("decode", p))
    emit("analysis", 5)
    sample = band_energy_db(x, sr, lambda p: emit("analysis", 10 + int(p * 0.75)))

    source = json.loads(Path(source_config_path).read_text(encoding="utf-8"))
    target = np.asarray(sample, dtype=float)
    if len(target) != len(BANDS):
        raise ValueError("Reference analysis must contain exactly 10 band values.")

    tolerance = source.get("tolerance_db", [1.5] * len(BANDS))
    weights = source.get("priority_weight", [1.0] * len(BANDS))
    if len(tolerance) != len(BANDS) or len(weights) != len(BANDS):
        raise ValueError("Selected config must contain 10 tolerance_db and priority_weight values.")

    emit("analysis", 90)
    emit("analysis", 100)

    return {
        "version": str(source.get("version", "0.1")),
        "target_db": [round(float(v), 2) for v in target],
        "tolerance_db": [round(float(v), 2) for v in tolerance],
        "priority_weight": [round(float(v), 2) for v in weights],
        "name": f"Reference — {path.stem}",
        "bpm": source.get("bpm"),
        "genre": source.get("genre", "Reference"),
        "notes": f"Generated from measured audio reference: {path.name}. 10-band target_db is the measured normalized band balance."
    }
