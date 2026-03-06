import traceback
from tests.test_predictor import test_extract_pos, test_score_driver_basic, test_score_driver_improvement, test_score_driver_negative_improvement, test_score_driver_overtake, test_score_driver_sprint, test_score_driver_sprint_bad, test_calculate_e_points_weighting

tests = [
    ("extract_pos", test_extract_pos),
    ("basic", test_score_driver_basic),
    ("improvement", test_score_driver_improvement),
    ("neg_improvement", test_score_driver_negative_improvement),
    ("overtake", test_score_driver_overtake),
    ("sprint", test_score_driver_sprint),
    ("sprint_bad", test_score_driver_sprint_bad),
    ("weighting", test_calculate_e_points_weighting)
]

for name, func in tests:
    print(f"Running {name}")
    try:
        func()
        print("PASS")
    except Exception as e:
        print("FAIL:", e)
        traceback.print_exc()
