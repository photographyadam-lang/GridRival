import pytest
import pandas as pd
import pulp
from optimizer import compute_salaries, run_optimizer

def test_compute_salaries_clamping():
    drivers_teams = pd.DataFrame([
        {'name': 'Driver Fast', 'type': 'DRIVER', 'salary': 10.0, 'code': 'A1'},
        {'name': 'Driver Slow', 'type': 'DRIVER', 'salary': 10.0, 'code': 'A1'},
        {'name': 'Team Good', 'type': 'TEAM', 'salary': 15.0, 'code': 'A1'},
        {'name': 'Team Bad', 'type': 'TEAM', 'salary': 15.0, 'code': 'A1'}
    ])
    
    # Mock e_points to force huge salary changes
    e_points = {
        ('Driver Fast', 1): 200.0, # Will be Rank 1 -> default ~30.0
        ('Driver Slow', 1): 0.0,   # Will be Rank 22 -> default ~5.0
        ('Team Good', 1): 200.0,   # Will be Rank 1 -> default ~28.0
        ('Team Bad', 1): 0.0       # Will be Rank 11 -> default ~4.0
    }
    
    salaries, deltas = compute_salaries(drivers_teams, e_points, start_round=1, horizon=1)
    
    # Driver max clamp is 2.0
    assert deltas[('Driver Fast', 1)] == 2.0
    assert deltas[('Driver Slow', 1)] == -2.0
    
    # Constructor max clamp is 3.0
    assert deltas[('Team Good', 1)] == 3.0
    assert deltas[('Team Bad', 1)] == -3.0

def test_compute_salaries_rounding():
    drivers_teams = pd.DataFrame([
        {'name': 'Driver Normal', 'type': 'DRIVER', 'salary': 15.0, 'code': 'A1'}
    ])
    
    # Force a specific rank. Rank 15 default is ~15.5
    # Let's say Rank 15 -> 15.5
    e_points = {('Driver Normal', 1): 50.0}
    salaries, deltas = compute_salaries(drivers_teams, e_points, start_round=1, horizon=1)
    
    # default 15.5 - 15.0 = 0.5 diff. Divided by 4 = 0.125
    # GridRival rule: Round down to nearest 0.1 -> 0.1
    assert deltas[('Driver Normal', 1)] == 0.1

from unittest.mock import patch

@patch('optimizer.calculate_e_points')
def test_run_optimizer_basic_execution(mock_calc):
    # Mocking calculate_e_points so we don't hit the live F1 API during tests
    mock_calc.return_value = pd.DataFrame([
        {'Driver': f'Driver_{i}', 'Type': 'DRIVER', 'Round': r, 'E_Points': 100.0} 
        for i in range(10) for r in [1, 2]
    ] + [
        {'Driver': 'Team_X', 'Type': 'TEAM', 'Round': r, 'E_Points': 200.0}
        for r in [1, 2]
    ])

    drivers_teams = pd.DataFrame([
        {'name': f'Driver_{i}', 'type': 'DRIVER', 'salary': 10.0, 'code': 'A1'} for i in range(10)
    ] + [
        {'name': 'Team_X', 'type': 'TEAM', 'salary': 15.0, 'code': 'A1'}
    ])
    
    hist_perf = pd.DataFrame() # empty fallback
    
    res = run_optimizer(drivers_teams, hist_perf, pd.DataFrame(), start_round=1, horizon=2)
    
    # Just mathematically verify it executed without crashing and built an active roster
    assert res is not None
    assert 'actions' in res
    
    # Verify exact roster size rules per round (5 drivers, 1 constructor)
    assert len(res['actions']) == 6
    drivers = [a for a in res['actions'] if a['type'] in ('DRIVER', 'TALENT')]
    teams = [a for a in res['actions'] if a['type'] == 'TEAM']
    assert len(drivers) == 5
    assert len(teams) == 1
