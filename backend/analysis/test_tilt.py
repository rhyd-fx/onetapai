"""Asserting tests for the tilt detector calibration."""
from mental.tilt_detector import detect_tilt

BASE = 1600000000


def test_tilting_session_flags_high():
    # Steady ACS decline + shrinking gaps (rage-queue) over 4 games.
    timestamps = [BASE, BASE + 2400, BASE + 4000, BASE + 5200]
    acs_values = [280, 240, 190, 150]
    sessions = detect_tilt(timestamps, acs_values)
    assert len(sessions) == 1
    s = sessions[0]
    # Should register meaningful tilt, but NOT instantly saturate to exactly 1.0
    # off a single factor.
    assert s.tilt_probability > 0.4, s.tilt_probability
    assert 0.0 <= s.tilt_probability <= 1.0
    # session_date must be a real ISO date, not an index like "0".
    assert s.session_date.startswith("2020-"), s.session_date
    # Honest decline figure: 280 -> 150 is ~46%.
    assert 40 < s.acs_decline_pct < 50, s.acs_decline_pct


def test_stable_session_not_flagged():
    # Normal variance, no real trend — must NOT be called tilt (significance gating).
    timestamps = [BASE, BASE + 2000, BASE + 4200]
    acs_values = [250, 200, 260]
    sessions = detect_tilt(timestamps, acs_values)
    assert len(sessions) == 1
    assert sessions[0].tilt_probability < 0.4, sessions[0].tilt_probability


def test_sessions_segmented_by_gap():
    # A >90-min gap splits into two sessions; each needs >=3 games to report.
    day1 = [BASE + i * 1800 for i in range(3)]           # 3 games, 30-min gaps
    day2 = [BASE + 100000 + i * 1800 for i in range(3)]  # big gap, then 3 more
    acs = [250, 240, 230, 260, 255, 250]
    sessions = detect_tilt(day1 + day2, acs)
    assert len(sessions) == 2, len(sessions)


if __name__ == "__main__":
    test_tilting_session_flags_high()
    test_stable_session_not_flagged()
    test_sessions_segmented_by_gap()
    print("All tilt tests passed.")
