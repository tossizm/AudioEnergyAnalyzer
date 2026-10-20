from dataclasses import dataclass
from typing import List

import numpy as np
from scipy.signal import stft, freqz

from app.models.result import EQRecommendation
from app.analysis.spectrum import BANDS, _peaking_biquad_coeffs


@dataclass
class RatioEQResult:
    pre_pct: np.ndarray
    target_pct: np.ndarray
    post_pct: np.ndarray
    residual_pct: np.ndarray
    eq: List[EQRecommendation]
    converged: bool
    iterations: int
    max_abs_error_pct: float
    eq_gains_db: np.ndarray


def validate_ratio_target(target_pct):
    vals = np.asarray(target_pct, dtype=float)
    if vals.shape != (len(BANDS),):
        raise ValueError("目標比率は現在の10バンド分必要です。")
    if not np.all(np.isfinite(vals)):
        raise ValueError("目標比率には有限の数値を入力してください。")
    # BAND10 (16000–20000 Hz) may be 0.00%; BAND1–BAND9 must remain > 0.
    if np.any(vals[:len(BANDS)-1] <= 0.0) or vals[-1] < 0.0:
        raise ValueError("BAND1～BAND9は0.00%より大きく、BAND10は0.00%以上にしてください。")
    total = float(np.sum(vals))
    if not np.isclose(total, 100.0, atol=1e-6):
        raise ValueError(f"目標比率の合計は100.00%にしてください（現在 {total:.2f}%）。")
    return vals


def default_ratio_from_target_db(target_db):
    db = np.asarray(target_db, dtype=float)
    if db.shape != (len(BANDS),):
        raise ValueError("target_db は現在の10バンド分必要です。")
    power = np.power(10.0, db / 10.0)
    total = float(np.sum(power))
    if not np.isfinite(total) or total <= 0.0:
        return np.full(len(BANDS), 100.0 / len(BANDS), dtype=float)
    return power / total * 100.0


def target_db_from_ratio(target_pct, reference_target_db):
    """Convert normalized energy percentages back to target dB.

    Percentages determine relative levels, not a unique absolute dB offset.
    Preserve the selected reference's mean target_db while replacing its
    relative band balance, so the round-trip percentage ratio remains exact.
    """
    pct = validate_ratio_target(target_pct)
    reference = np.asarray(reference_target_db, dtype=float)
    if reference.shape != (len(BANDS),) or not np.all(np.isfinite(reference)):
        raise ValueError("参照 target_db は10個の有限値が必要です。")
    raw_db = 10.0 * np.log10(np.maximum(pct, 1e-12) / 100.0)
    return raw_db + (float(np.mean(reference)) - float(np.mean(raw_db)))


def _spectrum_context(x, sr):
    mono = np.mean(np.asarray(x, dtype=float), axis=1)
    nperseg = min(32768, len(mono))
    if nperseg < 1024:
        nperseg = len(mono)
    # 50% overlap preserves useful resolution while cutting STFT work.
    noverlap = int(nperseg * 0.50) if nperseg > 1 else 0
    f, _, z = stft(
        mono,
        fs=sr,
        window="hann",
        nperseg=nperseg,
        noverlap=noverlap,
        boundary=None,
        padded=False,
    )
    psd = np.mean(np.abs(z) ** 2, axis=1)
    masks = [(f >= lo) & (f < hi) for lo, hi, _ in BANDS]
    return f, psd, masks


def _eq_templates(sr):
    templates = []
    nyquist = float(sr) / 2.0
    for lo, hi, _ in BANDS:
        freq = float(np.sqrt(lo * hi))
        if freq >= nyquist * 0.98:
            freq = max(10.0, nyquist * 0.94)
        q = float(np.clip(freq / max(hi - lo, 1e-9), 0.45, 2.0))
        templates.append((freq, q))
    return templates


def _post_pct_sr(context, sr, templates, gains_db):
    f, psd, masks = context
    response = np.ones_like(f, dtype=float)
    for (freq, q), gain in zip(templates, gains_db):
        if abs(float(gain)) < 1e-12:
            continue
        b, a = _peaking_biquad_coeffs(sr, freq, float(gain), q)
        _, h = freqz(b, a, worN=2.0 * np.pi * f / float(sr))
        response *= np.abs(h)
    post_psd = psd * np.square(response)
    powers = np.asarray([float(np.sum(post_psd[m])) for m in masks], dtype=float)
    total = float(np.sum(powers))
    if total <= 0.0:
        return np.zeros(len(BANDS), dtype=float)
    return powers / total * 100.0


def optimize_ratio_eq(
    x,
    sr,
    target_pct,
    *,
    max_iterations=12,
    tolerance_pct=0.05,
    max_gain_db=6.0,
    jacobian_step_db=0.10,
):
    """Find a set of per-band Bell EQ gains whose post-EQ 10-band occupancy matches target_pct.

    It starts from 10*log10(Target/Pre), then uses a damped numerical Jacobian so that
    adjacent-band EQ interaction is measured and corrected in a closed loop.
    """
    target = validate_ratio_target(target_pct)
    # A zero BAND10 target is valid as a reference value, but cannot be used
    # directly in logarithms. Use a tiny numerical floor only for optimization;
    # preserve the user's exact target (including 0.00%) in the reported result.
    target_math = np.maximum(target, 1e-8)
    target_math = target_math / np.sum(target_math) * 100.0
    arr = np.asarray(x, dtype=float)
    if arr.ndim == 1:
        arr = arr[:, None]
    if arr.ndim != 2 or arr.shape[0] < 1024:
        raise ValueError("EQ最適化には十分な長さのオーディオが必要です。")
    if not np.isfinite(arr).all():
        raise ValueError("オーディオデータに有限でない値があります。")

    context = _spectrum_context(arr, sr)
    templates = _eq_templates(sr)
    zero = np.zeros(len(BANDS), dtype=float)
    pre = _post_pct_sr(context, float(sr), templates, zero)
    safe_pre = np.maximum(pre, 1e-8)
    gains = np.clip(10.0 * np.log10(target_math / safe_pre), -max_gain_db, max_gain_db)
    post = _post_pct_sr(context, float(sr), templates, gains)

    def score(values):
        safe = np.maximum(values, 1e-8)
        return float(np.max(np.abs(10.0 * np.log10(safe / target_math))))

    current_score = score(post)
    iterations_done = 0

    for iteration in range(1, int(max_iterations) + 1):
        iterations_done = iteration
        residual_pct = target - post
        max_error = float(np.max(np.abs(residual_pct)))
        if max_error <= float(tolerance_pct):
            break

        y = 10.0 * np.log10(np.maximum(post, 1e-8) / target_math)
        jac = np.zeros((len(BANDS), len(BANDS)), dtype=float)
        for j in range(len(BANDS)):
            if gains[j] + jacobian_step_db <= max_gain_db - 1e-12:
                probe = gains.copy()
                probe[j] += jacobian_step_db
                y_probe = 10.0 * np.log10(np.maximum(_post_pct_sr(context, float(sr), templates, probe), 1e-8) / target_math)
                jac[:, j] = (y_probe - y) / jacobian_step_db
            elif gains[j] - jacobian_step_db >= -max_gain_db + 1e-12:
                probe = gains.copy()
                probe[j] -= jacobian_step_db
                y_probe = 10.0 * np.log10(np.maximum(_post_pct_sr(context, float(sr), templates, probe), 1e-8) / target_math)
                jac[:, j] = (y - y_probe) / jacobian_step_db
            else:
                jac[:, j] = 0.0

        try:
            delta, *_ = np.linalg.lstsq(jac, -y, rcond=1e-8)
        except np.linalg.LinAlgError:
            delta = -0.5 * y
        delta = np.nan_to_num(delta, nan=0.0, posinf=1.0, neginf=-1.0)
        delta = np.clip(delta, -2.0, 2.0)

        accepted = False
        for factor in (1.0, 0.5, 0.25, 0.125):
            trial_gains = np.clip(gains + delta * factor, -max_gain_db, max_gain_db)
            trial_post = _post_pct_sr(context, float(sr), templates, trial_gains)
            trial_score = score(trial_post)
            if trial_score + 1e-8 < current_score:
                gains, post, current_score = trial_gains, trial_post, trial_score
                accepted = True
                break

        if not accepted:
            break

    # The reported EQ uses 0.01 dB precision, so recalculate Post % from the
    # exact values that will be shown/saved to keep the result self-consistent.
    gains = np.round(gains, 2)
    post = _post_pct_sr(context, float(sr), templates, gains)
    eq = []
    for (lo, hi, name), (freq, q), gain in zip(BANDS, templates, gains):
        if abs(float(gain)) < 0.01:
            continue
        eq.append(EQRecommendation("Bell", round(float(freq), 1), round(float(gain), 2), round(float(q), 2)))

    residual = target - post
    max_error = float(np.max(np.abs(residual)))
    return RatioEQResult(
        pre_pct=np.asarray(pre, dtype=float),
        target_pct=np.asarray(target, dtype=float),
        post_pct=np.asarray(post, dtype=float),
        residual_pct=np.asarray(residual, dtype=float),
        eq=eq,
        converged=max_error <= float(tolerance_pct),
        iterations=iterations_done,
        max_abs_error_pct=max_error,
        eq_gains_db=np.asarray(gains, dtype=float),
    )
