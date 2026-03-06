import pytest
import pandas as pd
import numpy as np
from predictor import extract_pos, score_driver, calculate_e_points

def test_extract_pos():
    assert extract_pos('1') == 1.0
    assert extract_pos('1-2') == 1.5
    assert extract_pos('DNF') == 20.0
    assert extract_pos('WIN') == 1.0
    assert extract_pos(np.nan) == 20.0
    assert extract_pos('') == 20.0
    assert extract_pos('P3') == 3.0

def test_score_driver_basic():
    # pred_finish=1, avg_finish=1, quali_pos=1, teammate_finish=2
    # Base: 37 max(37, 100 - 0) = 100
    # Impr: 1 - 1 = 0
    # Over: 1 - 1 = 0
    # Team: 1 < 2 => 5
    # Total: 105
    score = score_driver(pred_finish=1.0, avg_finish=1.0, quali_pos=1.0, teammate_finish=2.0)
    assert score == 105.0

def test_score_driver_improvement():
    # pred_finish=5, avg_finish=10 (improvement of 5)
    # quali=5, teammate=6
    # Base: 100 - 4*3 = 88
    # Impr: 5 * 10 = 50
    # Over: 0
    # Team: 5 < 6 => 5
    # Total: 88 + 50 + 5 = 143
    score = score_driver(pred_finish=5.0, avg_finish=10.0, quali_pos=5.0, teammate_finish=6.0)
    assert score == 143.0

def test_score_driver_negative_improvement():
    # pred_finish=10, avg_finish=5 (loss of -5) -> -50
    # Base: 100 - 9*3 = 73
    # Impr: -50
    # Over: 0
    # Team: 10 > 9 (no bonus) => 0
    # Total: 73 - 50 = 23 (but usually bounded or not let's see)
    score = score_driver(pred_finish=10.0, avg_finish=5.0, quali_pos=10.0, teammate_finish=9.0)
    assert score == 23.0

def test_score_driver_overtake():
    # pred=5, quali=10 => overtake=5 => 25 pts
    # avg=5 => impr=0
    # base=88, team=5
    # Total: 88 + 0 + 25 + 5 = 118
    score = score_driver(pred_finish=5.0, avg_finish=5.0, quali_pos=10.0, teammate_finish=6.0)
    assert score == 118.0

def test_score_driver_sprint():
    # pred=1, avg=1, quali=1, team=2, sprint=True, avg_sprint=1
    # feature = 105
    # sprint = max(0, 15 - 0) = 15
    # Total: 120
    score = score_driver(pred_finish=1.0, avg_finish=1.0, quali_pos=1.0, teammate_finish=2.0, has_sprint=True, avg_sprint_finish=1.0)
    assert score == 120.0

def test_score_driver_sprint_bad():
    # sprint=True, avg_sprint=11 => 15 - 15 = 0
    score = score_driver(pred_finish=1.0, avg_finish=1.0, quali_pos=1.0, teammate_finish=2.0, has_sprint=True, avg_sprint_finish=11.0)
    assert score == 105.0

def test_calculate_e_points_weighting():
    # Mock data to verify exponential weighting works
    drivers = pd.DataFrame([
        {'name': 'Driver A', 'code': 'A1', 'type': 'DRIVER'},
        {'name': 'Driver B', 'code': 'A1', 'type': 'DRIVER'}
    ])
    teams = pd.DataFrame([
        {'name': 'Team A', 'code': 'A1', 'salary': 20.0, 'type': 'TEAM'}
    ])
    
    # Driver A has good 2025 results, bad 2023. Driver B has bad 2025, good 2023.
    # We expect Driver A to have a much better average finish.
    hist_perf = pd.DataFrame([
        {'driver_name': 'Driver A', 'race_finish': '1', 'year': 2025, 'round': 1},
        {'driver_name': 'Driver A', 'race_finish': '20', 'year': 2023, 'round': 1},
        {'driver_name': 'Driver B', 'race_finish': '20', 'year': 2025, 'round': 1},
        {'driver_name': 'Driver B', 'race_finish': '1', 'year': 2023, 'round': 1},
    ])
    
    rounds = pd.DataFrame([
        {'round': 4, 'track_type': 'TEST', 'has_sprint': False}
    ])
    
    # Run
    df = calculate_e_points(drivers, teams, hist_perf, rounds)
    assert not df.empty
    
    # Check E_Points
    pts_a = df[df['Driver'] == 'Driver A']['E_Points'].values[0]
    pts_b = df[df['Driver'] == 'Driver B']['E_Points'].values[0]
    
    assert pts_a > pts_b, "Exponential weighting should heavily favor 2025 finishes over 2023"
