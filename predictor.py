import pandas as pd
import numpy as np
import re
import os

# Base directory for the CSVs
BASE_DIR = r"c:\Users\adam\OneDrive\Documents\projects\gridrival-optimizer"

def load_data():
    drivers_teams = pd.read_csv(os.path.join(BASE_DIR, "GridRivals - drivers and teams.csv"))
    hist_perf = pd.read_csv(os.path.join(BASE_DIR, "GridRivals - historical performance.csv"))
    rounds = pd.read_csv(os.path.join(BASE_DIR, "GridRivals - rounds.csv"))
    
    # Clean driver salaries (handle any team salaries vs driver)
    drivers = drivers_teams[drivers_teams['type'] == 'DRIVER'].copy()
    teams = drivers_teams[drivers_teams['type'] == 'TEAM'].copy()
    
    return drivers, teams, hist_perf, rounds

def position_to_points(pos_str):
    pos_str = str(pos_str).upper()
    if pos_str == 'DNF':
        return 0
    if 'WIN' in pos_str:
        return 100
    if '-' in pos_str: # e.g. "1-3"
        parts = pos_str.split('-')
        avg_pos = (float(parts[0]) + float(parts[1])) / 2
        return max(0, 100 - (avg_pos - 1) * 3) # rough proxy
        
    try:
        # try to parse as number
        pos = float(re.findall(r'\d+', pos_str)[0])
        # GridRival finish table rough approximation:
        # 1st -> 100, 2nd -> 97, ... (-3 per position)
        return max(0, 100 - (pos - 1) * 3)
    except:
        return 0

def calculate_e_points(drivers, teams, hist_perf, rounds):
    # Setup team salaries for team proxy
    team_salaries = dict(zip(teams['code'], teams['salary']))
    max_team_salary = max(team_salaries.values()) if team_salaries else 1.0
    
    # Process historical data
    hist_perf['implied_points'] = hist_perf['race_finish_or_range'].apply(position_to_points)
    
    # Join with rounds to get track type
    hist_perf = hist_perf.merge(rounds[['round', 'track_type']], on='round', how='left')
    
    # Determine the next 4 rounds (rounds 4, 5, 6, 7 based on data)
    future_rounds = rounds[rounds['round'].between(4, 7)]
    
    predictions = []
    
    for _, driver_row in drivers.iterrows():
        driver = driver_row['name']
        team_code = driver_row['code']
        
        # Historical for this driver
        d_hist = hist_perf[hist_perf['driver_name'] == driver]
        
        # Recent Form (last 3 available)
        recent = d_hist[d_hist['round'] <= 3]
        if not recent.empty:
            recent_form_points = recent['implied_points'].mean()
        else:
            recent_form_points = 50.0 # fallback
            
        # Team Proxy
        team_salary = team_salaries.get(team_code, 10.0)
        # Assuming max team salary corresponds to ~100 points, min to ~20
        team_proxy_points = (team_salary / max_team_salary) * 100.0
        
        for _, round_row in future_rounds.iterrows():
            r = round_row['round']
            t_type = round_row['track_type']
            
            # Track Fit
            track_hist = d_hist[d_hist['track_type'] == t_type]
            if not track_hist.empty:
                track_fit_points = track_hist['implied_points'].mean()
            else:
                track_fit_points = recent_form_points # fallback to recent form
                
            # Weighted Average
            # Let's say: 40% Recent Form, 30% Track Fit, 30% Team Proxy
            e_points = (0.4 * recent_form_points) + (0.3 * track_fit_points) + (0.3 * team_proxy_points)
            
            predictions.append({
                'Driver': driver,
                'Round': r,
                'Track': round_row['circuit'],
                'E_Points': round(e_points, 1)
            })
            
    return pd.DataFrame(predictions)

if __name__ == "__main__":
    drivers, teams, hist_perf, rounds = load_data()
    pred_df = calculate_e_points(drivers, teams, hist_perf, rounds)
    
    # Pivot for summary table
    summary = pred_df.pivot(index='Driver', columns='Round', values='E_Points')
    summary['Average'] = summary.mean(axis=1).round(1)
    summary = summary.sort_values(by='Average', ascending=False)
    
    print("=== Predicted Points (E_Points) for Next 4 Rounds ===")
    print(summary.to_string())
