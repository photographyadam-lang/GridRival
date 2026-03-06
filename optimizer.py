import pandas as pd
import numpy as np
import pulp
import os
import re
import json
from predictor import calculate_e_points, load_local_data

BASE_DIR = r"c:\Users\adam\OneDrive\Documents\projects\gridrival-optimizer"

def load_data():
    drivers_teams = pd.read_csv(os.path.join(BASE_DIR, "GridRivals - drivers and teams.csv"))
    hist_perf = pd.read_csv(os.path.join(BASE_DIR, "GridRivals - historical performance.csv"))
    rounds = pd.read_csv(os.path.join(BASE_DIR, "GridRivals - rounds.csv"))
    current_team = pd.read_csv(os.path.join(BASE_DIR, "GridRivals - current team.csv"))
    return drivers_teams, hist_perf, rounds, current_team

def parse_position(pos_str):
    pos_str = str(pos_str).upper()
    if pos_str == 'DNF' or 'Q' in pos_str:
        return 20 # Assume back
    if 'WIN' in pos_str:
        return 1
    if '-' in pos_str:
        parts = pos_str.split('-')
        return (float(parts[0]) + float(parts[1])) / 2
    try:
        numbers = re.findall(r'\d+', pos_str)
        if numbers:
            return float(numbers[0])
        return 20
    except:
        return 20

def pos_to_points_driver(pos):
    # Base points map
    table = {1:100, 2:97, 3:94, 4:91, 5:88, 6:85, 7:82, 8:79, 9:76, 10:73,
             11:70, 12:67, 13:64, 14:61, 15:58, 16:55, 17:52, 18:49, 19:46, 20:43, 21:40, 22:37}
    if pos in table:
        return table[pos]
    if pos < 1: return 100
    if pos > 22: return 37
    # Linear interpolation
    lower = int(np.floor(pos))
    upper = int(np.ceil(pos))
    if lower == upper:
        return table.get(lower, 37)
    return table.get(lower, 37) + (pos - lower) * (table.get(upper, 37) - table.get(lower, 37))

def pos_to_points_constructor(pos):
    # Race points + Quali points rough approx
    race_table = {1:60, 2:58, 3:56, 4:54, 5:52, 6:50, 7:48, 8:46, 9:44, 10:42,
                  11:40, 12:38, 13:36, 14:34, 15:32, 16:30, 17:28, 18:26, 19:24, 20:22, 21:20, 22:18}
    quali_table = {1:30, 2:29, 3:28, 4:27, 5:26, 6:25, 7:24, 8:23, 9:22, 10:21,
                   11:20, 12:19, 13:18, 14:17, 15:16, 16:15, 17:14, 18:13, 19:12, 20:11, 21:10, 22:9}
    
    val1 = race_table.get(min(max(int(round(pos)), 1), 22), 18)
    val2 = quali_table.get(min(max(int(round(pos)), 1), 22), 9)
    return val1 + val2

def generate_expected_points(drivers_teams, hist_perf, rounds_df, start_round=4, horizon=5):
    target_rounds = list(range(start_round, start_round + horizon))
    e_points = {} # (entity, round) -> points
    
    # Process historical
    hist_perf['pos'] = hist_perf['race_finish_or_range'].apply(parse_position)
    
    for _, row in drivers_teams.iterrows():
        entity = row['name']
        is_driver = (row['type'] == 'DRIVER')
        
        hist_e = hist_perf[hist_perf['driver_name'] == entity] # assuming constructors don't have direct history in this simplistic view
        # We need a team mapping if it's a CONSTRUCTOR. For now, estimate constructor points from top driver + 50% second driver
        
        if is_driver:
            avg_pos = hist_e['pos'].mean() if len(hist_e) > 0 else 15.0
            for r in target_rounds:
                # Add a little noise or track type adj if needed, for now use historical avg pos
                e_points[(entity, r)] = pos_to_points_driver(avg_pos)
        else:
            # Let's derive team strength from salary vs max salary
            team_salary = row['salary']
            max_tsal = drivers_teams[drivers_teams['type'] == 'TEAM']['salary'].max()
            # team points roughly 35-90 depending on strength
            expected_c_points = 35 + (team_salary / max_tsal) * 55
            for r in target_rounds:
                e_points[(entity, r)] = expected_c_points
                
    return e_points

def compute_salaries(drivers_teams, e_points, start_round=4, horizon=5):
    # Implements Section 7 GridRival_F1_Rules Salary Adjustment
    start_salaries = dict(zip(drivers_teams['name'], drivers_teams['salary']))
    
    # For Drivers
    default_driver_salary = {
        1:34.0, 2:32.4, 3:30.8, 4:29.2, 5:27.6, 6:26.0, 7:24.4, 8:22.8, 9:21.2, 10:19.6,
        11:18.0, 12:16.4, 13:14.8, 14:13.2, 15:11.6, 16:10.0, 17:8.4, 18:6.8, 19:5.2, 20:3.6,
        21:2.0, 22:0.4
    }
    # For Constructors
    default_constructor_salary = {
        1:30.0, 2:27.4, 3:24.8, 4:22.2, 5:19.6, 6:17.0, 7:14.4, 8:11.8, 9:9.2, 10:6.6,
        11:4.0 # fill up to 11
    }
    
    salaries = {} # (entity, round) -> salary before round starts (in millions)
    deltas = {} # (entity, round) -> delta change AFTER round
    
    for entity in start_salaries:
        salaries[(entity, start_round)] = start_salaries[entity]
        
    for t in range(start_round, start_round + horizon):
        # Rank drivers this round
        driver_points = [(e, e_points[(e,t)]) for e in drivers_teams[drivers_teams['type']=='DRIVER']['name']]
        driver_points.sort(key=lambda x: x[1], reverse=True)
        driver_ranks = {x[0]: i+1 for i, x in enumerate(driver_points)}
        
        # Rank constructors this round
        team_points = [(e, e_points[(e,t)]) for e in drivers_teams[drivers_teams['type']=='TEAM']['name']]
        team_points.sort(key=lambda x: x[1], reverse=True)
        team_ranks = {x[0]: i+1 for i, x in enumerate(team_points)}
        
        for entity in start_salaries.keys():
            # We break loop if not in team_ranks or driver_ranks
            if entity in driver_ranks:
                rank = min(driver_ranks[entity], 22)
                default_s = default_driver_salary.get(rank, 0.4)
                max_adj = 2.0
            elif entity in team_ranks:
                rank = min(team_ranks[entity], 11)
                default_s = default_constructor_salary.get(rank, 4.0)
                max_adj = 3.0
            else:
                # If unranked, salary remains the same
                deltas[(entity, t)] = 0.0
                if t + 1 < start_round + horizon:
                    salaries[(entity, t+1)] = salaries.get((entity, t), start_salaries[entity])
                continue
                
            s_before = salaries.get((entity, t), start_salaries[entity])
            base_var = default_s - s_before
            adj_raw = base_var / 4.0
            
            # The "Smoothing" Formula
            # Round down to nearest 0.1M
            adj_rounded = np.floor(adj_raw * 10) / 10.0
            
            # Clamp between -max_adj and max_adj
            adj_clamped = max(min(adj_rounded, max_adj), -max_adj)
            
            deltas[(entity, t)] = adj_clamped
            if t + 1 < start_round + horizon:
                salaries[(entity, t+1)] = s_before + adj_clamped
                
    return salaries, deltas

def run_optimizer(drivers_teams, hist_perf, current_team, start_round=4, horizon=5, GAMMA=1.0):
    # Retrieve predictions from our new predictor module
    rounds_df = pd.read_csv(os.path.join(BASE_DIR, "GridRivals - rounds.csv")) if os.path.exists(os.path.join(BASE_DIR, "GridRivals - rounds.csv")) else pd.DataFrame()
    pred_df = calculate_e_points(drivers_teams, drivers_teams[drivers_teams['type']=='TEAM'], hist_perf, rounds_df)
    
    e_points = {}
    if not pred_df.empty:
        for _, row in pred_df.iterrows():
            e_points[(row['Driver'], row['Round'])] = row['E_Points']
            # Also store with type for team mapping just in case
            e_points[(row['Driver'], row['Round'], row['Type'])] = row['E_Points']
    else:
        # Fallback if prediction fails
        return None
        
    try:
        salaries, deltas = compute_salaries(drivers_teams, e_points, start_round, horizon)
    except KeyError as e:
        print(f"KeyError in compute_salaries: {e}")
        return {"error": f"KeyError in compute_salaries: {e}"}
    
    rounds = list(range(start_round, start_round + horizon))
    if drivers_teams.empty:
        return None
    elements = list(drivers_teams['name'])
    is_driver = {row['name']: (row['type'] == 'DRIVER') for _, row in drivers_teams.iterrows()}
    
    # Define PuLP problem
    prob = pulp.LpProblem("GridRival_Optimizer", pulp.LpMaximize)
    
    # Variables
    # x[e,t]: Is element e on roster during round t?
    x = pulp.LpVariable.dicts("x", ((e, t) for e in elements for t in rounds), cat='Binary')
    
    # T_var[e,t]: Is element e the Talent driver during round t?
    T_var = pulp.LpVariable.dicts("T", ((e, t) for e in elements for t in rounds), cat='Binary')
    
    # z[e, t_start, length]: Did we start a contract for e at t_start of length L?
    lengths = [1, 2, 3, 4, 5]
    z = pulp.LpVariable.dicts("z", ((e, t_start, l) for e in elements for t_start in rounds for l in lengths), cat='Binary')
    
    # sell[e, t]: Did we early release e BEFORE round t? (Let's keep it simple: no early release penalities initially. Just binding z to x)
    # x[e,t] sum(z[e, t_start, L]) where t_start <= t < t_start + L
    for e in elements:
        for t in rounds:
            valid_contracts = []
            for t_start in rounds:
                if t_start <= t:
                    for l in lengths:
                        if t_start + l > t:
                            valid_contracts.append(z[e, t_start, l])
            prob += x[e, t] == pulp.lpSum(valid_contracts), f"Roster_State_{e}_{t}"
            
    # Cannot start overlapping contracts
    for e in elements:
        prob += pulp.lpSum(z[e, t, l] for t in rounds for l in lengths) <= (horizon + 4) // 5 + 2, f"Max_Contracts_{e}"
        
    # Cooldown constraint: if a contract ends before round t (i.e., started at t_prev with length l_prev such that t_prev + l_prev == t),
    # we CANNOT start a new contract at round t.
    for e in elements:
        for t in rounds:
            # All contracts ending exactly at round t
            ending_contracts = []
            for t_prev in rounds:
                if t_prev < t:
                    for l_prev in lengths:
                        if t_prev + l_prev == t:
                            ending_contracts.append(z[e, t_prev, l_prev])
            
            # All contracts starting exactly at round t
            starting_contracts = [z[e, t, l] for l in lengths]
            
            if ending_contracts and starting_contracts:
                prob += pulp.lpSum(ending_contracts) + pulp.lpSum(starting_contracts) <= 1, f"Cooldown_{e}_{t}"
            
            
    # Exact Roster Requirements
    for t in rounds:
        prob += pulp.lpSum(x[e, t] for e in elements if is_driver[e]) == 5, f"5_Drivers_{t}"
        prob += pulp.lpSum(x[e, t] for e in elements if not is_driver[e]) == 1, f"1_Constructor_{t}"
        prob += pulp.lpSum(T_var[e, t] for e in elements) == 1, f"1_Talent_{t}"
        
    # Talent constraints
    for t in rounds:
        for e in elements:
            if not is_driver[e]:
                prob += T_var[e, t] == 0, f"Not_Talent_Const_{e}_{t}"
            else:
                # Must be on roster
                prob += T_var[e, t] <= x[e, t], f"Talent_On_Roster_{e}_{t}"
                    # Must be affordable (salary <= 18.0)
                if salaries[(e, t)] > 18.0:
                    prob += T_var[e, t] == 0, f"Talent_Salary_Cap_{e}_{t}"
                    
    # Current Team Constraints
    if current_team is not None and not current_team.empty:
        for _, row in current_team.iterrows():
            e = row['name']
            l_rem = int(row.get('length_remaining', 1))
            if e in elements and l_rem > 0:
                for i in range(min(l_rem, horizon)):
                    prob += x[e, start_round + i] == 1, f"CustomTeam_Lock_{e}_{start_round+i}"
                    
    # Dynamic Budget Constraints
    # Initial budget: 100.0 (let's assume 100M total budget)
    initial_budget = 100.0
    for t in rounds:
        # Portfolio value before round t
        # PV_t = Initial + sum_{tau=start}^{t-1} sum_{e} (delta_S[e, tau] * x[e, tau])
        budget_grown = initial_budget
        # Add a placeholder for PV expression
        pv_expr = initial_budget + pulp.lpSum(deltas[(e, tau)] * x[e, tau] for e in elements for tau in rounds if tau < t)
        
        # Total salary of active roster cannot exceed PV_t
        cost_expr = pulp.lpSum(salaries[(e, t)] * x[e, t] for e in elements)
        
        prob += cost_expr <= pv_expr, f"Budget_{t}"
        
    # Objective Function
    # sum( points + gamma * delta PV ) - Early Season Uncertainty Penalty
    try:
        obj_points = pulp.lpSum((e_points[(e, t)] * x[e, t]) + (e_points[(e, t)] * T_var[e, t]) for e in elements for t in rounds)
    except KeyError as e:
        print(f"KeyError in Objective processing points for {e}")
        return {"error": f"KeyError in Objective points: {e}"}
        
    # Early Season Contract Penalty: applies to contracts length >= 3. Scales inversely with start_round (t)
    base_risk = 3.0 # Points penalty multiplier
    penalty_expr = pulp.lpSum(
        base_risk * (l - 2) * max(0, (8 - t) / 7.0) * z[e, t, l] 
        for e in elements for t in rounds for l in lengths if l >= 3
    )
        
    obj_growth = pulp.lpSum(deltas[(e, t)] * x[e, t] for e in elements for t in rounds)
    
    prob += obj_points - penalty_expr + GAMMA * obj_growth, "Objective"
    
    # Solve
    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    
    if pulp.LpStatus[prob.status] != "Optimal":
        print("No optimal solution found! Status:", pulp.LpStatus[prob.status])
        return
        
    print(f"=== Action Plan (Round {start_round}) | Gamma={GAMMA} ===")
    print(f"Expected Utility Score: {pulp.value(prob.objective):.1f}")
    
    # Reconstruct PV and actual values for printing
    pv = initial_budget
    total_cost = 0
    t = start_round
    actions = []
    
    for e in elements:
        if x[e, t].varValue is not None and x[e, t].varValue > 0.5:
            total_cost += salaries[(e,t)]
            is_talent = (T_var[e, t].varValue is not None and T_var[e, t].varValue > 0.5)
            
            # Find contract length
            contract_l = 1
            for l in lengths:
                if z[e, t, l].varValue is not None and z[e, t, l].varValue > 0.5:
                    contract_l = l
                    break
                    
            if is_talent:
                actions.append(f"TALENT: {e} (Price: {salaries[(e,t)]:.1f}M, Length: {contract_l})")
            elif is_driver[e]:
                actions.append(f"BUY/HOLD: {e} (Length: {contract_l})")
            else:
                actions.append(f"TEAM: {e} (Length: {contract_l})")
                
    # PV growth approx
    growth = sum(deltas[(e, tau)] * x[e, tau].varValue for e in elements for tau in rounds if x[e, tau].varValue > 0.5)
    
    print(f"Current PV: {pv:.1f}M | Roster Cost: {total_cost:.1f}M")
    for a in sorted(actions):
        print("- " + a)
    print(f"PROJECTED BUDGET GROWTH by Round {rounds[-1]}: +${growth:.1f}M")
    print("=" * 50)
    
    # Return structured data for the dashboard
    parsed_actions = []
    for e in elements:
        if x[e, t].varValue is not None and x[e, t].varValue > 0.5:
            is_talent = (T_var[e, t].varValue is not None and T_var[e, t].varValue > 0.5)
            c_l = 1
            for l in lengths:
                if z[e, t, l].varValue is not None and z[e, t, l].varValue > 0.5:
                    c_l = l
            if is_talent:
                parsed_actions.append({'name': e, 'type': 'TALENT', 'price': round(salaries[(e,t)], 1), 'length': c_l})
            elif is_driver[e]:
                parsed_actions.append({'name': e, 'type': 'DRIVER', 'price': round(salaries[(e,t)], 1), 'length': c_l})
            else:
                parsed_actions.append({'name': e, 'type': 'TEAM', 'price': round(salaries[(e,t)], 1), 'length': c_l})
    
    return {
        'gamma': GAMMA,
        'expected_utility': round(pulp.value(prob.objective), 1),
        'current_pv': round(pv, 1),
        'roster_cost': round(total_cost, 1),
        'budget_growth': round(growth, 1),
        'actions': parsed_actions
    }

    # This block can remain for debugging, but app.py drives main execution now
    pass
