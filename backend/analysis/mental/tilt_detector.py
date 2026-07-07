from datetime import datetime, timezone

import numpy as np
from dataclasses import dataclass
from scipy import stats as scipy_stats


@dataclass
class TiltAnalysis:
    session_date: str                 # ISO date of the session's first match
    match_count: int
    acs_trajectory: list[float]       # ACS per match, chronological
    acs_slope: float                  # Linear regression slope (ACS per match)
    acs_r_squared: float              # How well the trend fits a line
    acs_decline_pct: float            # First-match ACS → last-match ACS, as %
    inter_match_gaps_min: list[float] # Minutes between matches
    avg_gap_min: float
    tilt_probability: float           # 0.0–1.0
    recommendation: str


def detect_tilt(
    match_timestamps: list[float],    # Unix timestamps, chronological
    match_acs_values: list[float],
    session_gap_threshold_min: float = 90.0,  # >90 min gap = new session
) -> list[TiltAnalysis]:
    """
    Segment matches into sessions and score tilt from three weighted, capped
    signals (so no single factor can saturate the probability):

    - Factor 1 (weight 0.5): a statistically SIGNIFICANT ACS decline. The slope
      is normalized by mean ACS, scaled by severity, and discounted heavily when
      the linear fit is not significant (p >= 0.10) — this prevents tiny-sample
      noise from reading as tilt.
    - Factor 2 (weight 0.2): rage-queueing — inter-match gaps shrinking over time.
    - Factor 3 (weight 0.3): late-session collapse — second-half ACS below first.
    """
    # Segment into sessions by the inter-match gap threshold.
    sessions: list[list[int]] = []
    current_session = [0]
    for i in range(1, len(match_timestamps)):
        gap_min = (match_timestamps[i] - match_timestamps[i - 1]) / 60.0
        if gap_min > session_gap_threshold_min:
            sessions.append(current_session)
            current_session = [i]
        else:
            current_session.append(i)
    if match_timestamps:
        sessions.append(current_session)

    results: list[TiltAnalysis] = []
    for session_indices in sessions:
        if len(session_indices) < 3:
            continue  # Need at least 3 matches for a meaningful trend

        acs_vals = [float(match_acs_values[i]) for i in session_indices]
        timestamps = [float(match_timestamps[i]) for i in session_indices]

        # Linear regression on the ACS trajectory.
        x = np.arange(len(acs_vals))
        slope, intercept, r_value, p_value, std_err = scipy_stats.linregress(x, acs_vals)
        r_squared = float(r_value ** 2) if not np.isnan(r_value) else 0.0

        # Inter-match gaps (minutes).
        gaps = [(timestamps[i + 1] - timestamps[i]) / 60.0 for i in range(len(timestamps) - 1)]
        avg_gap = float(np.mean(gaps)) if gaps else 0.0

        # Are gaps shrinking over the session (rage-queueing)?
        gap_slope = 0.0
        if len(gaps) >= 2:
            gap_slope = float(scipy_stats.linregress(np.arange(len(gaps)), gaps)[0])

        mean_acs = float(np.mean(acs_vals))
        normalized_slope = (slope / mean_acs) if mean_acs > 0 else 0.0

        # Factor 1 — significant ACS decline (up to 0.5).
        factor_decline = 0.0
        if normalized_slope < 0:
            severity = min(1.0, -normalized_slope / 0.10)  # a 10%/match drop = full severity
            significant = (not np.isnan(p_value)) and (p_value < 0.10)
            confidence = 1.0 if significant else 0.25       # discount noisy/insignificant trends
            factor_decline = 0.5 * severity * confidence

        # Factor 2 — rage-queueing (up to 0.2).
        factor_rage = min(0.2, abs(gap_slope) * 0.02) if gap_slope < 0 else 0.0

        # Factor 3 — late-session collapse (up to 0.3).
        factor_collapse = 0.0
        if len(acs_vals) >= 4:
            half = len(acs_vals) // 2
            first_half = float(np.mean(acs_vals[:half]))
            second_half = float(np.mean(acs_vals[half:]))
            if first_half > 0:
                collapse_ratio = (first_half - second_half) / first_half
                factor_collapse = max(0.0, min(0.3, collapse_ratio * 0.6))

        tilt_probability = float(min(1.0, factor_decline + factor_rage + factor_collapse))

        # Honest session decline: first match ACS → last match ACS.
        decline_pct = ((acs_vals[0] - acs_vals[-1]) / acs_vals[0] * 100) if acs_vals[0] > 0 else 0.0

        if tilt_probability > 0.7:
            rec = (
                "🛑 HIGH TILT DETECTED. Stop queueing immediately. Take a 30-minute "
                "break with physical movement. Your ACS fell {:.0f}% from your first "
                "to last game this session."
            ).format(max(0.0, decline_pct))
        elif tilt_probability > 0.4:
            rec = (
                "⚠️ Moderate tilt detected. Consider a 10–15 minute break. Play a DM "
                "or Spike Rush to reset before your next ranked game."
            )
        else:
            rec = "✅ Mental state appears stable. Continue playing."

        session_date = (
            datetime.fromtimestamp(timestamps[0], tz=timezone.utc).date().isoformat()
        )

        results.append(TiltAnalysis(
            session_date=session_date,
            match_count=len(session_indices),
            acs_trajectory=acs_vals,
            acs_slope=float(slope),
            acs_r_squared=r_squared,
            acs_decline_pct=float(decline_pct),
            inter_match_gaps_min=gaps,
            avg_gap_min=avg_gap,
            tilt_probability=tilt_probability,
            recommendation=rec,
        ))

    return results
