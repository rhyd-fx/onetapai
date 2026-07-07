import numpy as np
from spatial.peek_classifier import MapGeometry, classify_peek
from mechanical.aim_profiler import AimProfile
from mechanical.drill_prescriber import prescribe_drills, PlayerHardwareProfile

def test_peek_classifier():
    # Dummy geometry for testing
    wall_segments = np.array([
        [[0.0, 0.0], [100.0, 0.0]],
        [[0.0, 0.0], [0.0, 100.0]]
    ])
    choke_points = np.array([[50.0, 50.0]])
    common_angles = np.array([[10.0, 10.0]])

    geo = MapGeometry(wall_segments, choke_points, common_angles)

    death_pos = np.array([10.0, 10.0])
    killer_pos = np.array([20.0, 20.0])

    peek_type = classify_peek(death_pos, killer_pos, geo)
    print(f"Test Peek Type: {peek_type}")

def test_aim_profiler():
    stats = {
        "headshot_pct": 0.15,
        "bodyshot_pct": 0.60,
        "legshot_pct": 0.25,
        "hs_by_range": {"short": 0.20, "long": 0.05},
        "bs_by_econ": {"eco": 0.60, "full_buy": 0.50},
        "opening_hs_pct": 0.10,
        "zero_damage_death_pct": 0.30
    }
    
    profile = AimProfile.from_db_stats(stats)
    print(f"Test Aim Deficiencies: {[d.value for d in profile.deficiencies]}")
    
    # 1600 DPI, 0.25 sens = 400 eDPI
    hw = PlayerHardwareProfile(mouse_dpi=1600, in_game_sens=0.25, edpi=400.0)
    drills = prescribe_drills(profile, hw)
    print(f"Prescribed {len(drills)} drills for 400 eDPI")
    for d in drills:
        print(f"- {d.drill_name} on {d.platform}: {d.focus}")
        
if __name__ == "__main__":
    test_peek_classifier()
    test_aim_profiler()
