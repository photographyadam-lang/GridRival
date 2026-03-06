import pandas as pd
import numpy as np
import re
import os
import datetime
import requests
import json

# Base directory for the CSVs
BASE_DIR = r"c:\Users\adam\OneDrive\Documents\projects\gridrival-optimizer"

def load_api_data(year, meeting_key):
    # Base URL for OpenF1
    base_url = "https://api.openf1.org/v1"
    
    try:
        # Fetch sessions
        sessions = requests.get(f"{base_url}/sessions?year={year}&meeting_key={meeting_key}").json()
        fp1_session_key, fp2_session_key, fp3_session_key, quali_session_key, race_session_key = None, None, None, None, None
        
        for s in sessions:
            if s['session_name'] == 'Practice 1':
                fp1_session_key = s['session_key']
            elif s['session_name'] == 'Practice 2':
                fp2_session_key = s['session_key']
            elif s['session_name'] == 'Practice 3':
                fp3_session_key = s['session_key']
            elif s['session_name'] == 'Qualifying':
                quali_session_key = s['session_key']
            elif s['session_name'] == 'Race':
                race_session_key = s['session_key']
                
        return {
            'fp1': fp1_session_key,
            'fp2': fp2_session_key,
            'fp3': fp3_session_key,
            'quali': quali_session_key,
            'race': race_session_key,
            'base_url': base_url
        }
    except Exception as e:
        print(f"Error fetching from OpenF1: {e}")
        return None

def fetch_driver_mapping(base_url, meeting_key):
    """Fetches driver data to map driver_number -> name_acronym (GridRival Code)"""
    mapping = {}
    try:
        drivers = requests.get(f"{base_url}/drivers?meeting_key={meeting_key}").json()
        for d in drivers:
            mapping[d['driver_number']] = d['name_acronym']
        return mapping
    except Exception as e:
        print(f"Error fetching drivers: {e}")
        return {}

def fetch_laps(base_url, session_key):
    if not session_key: return []
    try:
        url = f"{base_url}/laps?session_key={session_key}"
        return requests.get(url).json()
    except: return []

def fetch_positions(base_url, session_key):
    if not session_key: return []
    try:
        url = f"{base_url}/positions?session_key={session_key}"
        return requests.get(url).json()
    except: return []

def load_local_data():
    drivers_teams_path = os.path.join(BASE_DIR, "GridRivals - drivers and teams.csv")
    hist_perf_path = os.path.join(BASE_DIR, "GridRivals - historical performance.csv")
    rounds_path = os.path.join(BASE_DIR, "GridRivals - rounds.csv")
    
    drivers_teams = pd.read_csv(drivers_teams_path, encoding='latin1') if os.path.exists(drivers_teams_path) else pd.DataFrame()
    hist_perf = pd.read_csv(hist_perf_path, encoding='latin1') if os.path.exists(hist_perf_path) else pd.DataFrame()
    rounds = pd.read_csv(rounds_path, encoding='latin1') if os.path.exists(rounds_path) else pd.DataFrame()
    
    drivers = pd.DataFrame()
    teams = pd.DataFrame()
    
    if not drivers_teams.empty:
        drivers = drivers_teams[drivers_teams['type'] == 'DRIVER'].copy()
        teams = drivers_teams[drivers_teams['type'] == 'TEAM'].copy()
        
    return drivers, teams, hist_perf, rounds

def position_to_points(pos_str):
    pos_str = str(pos_str).upper()
    if pos_str == 'DNF': return 43
    if 'WIN' in pos_str: return 100
    if '-' in pos_str:
        parts = pos_str.split('-')
        avg_pos = (float(parts[0]) + float(parts[1])) / 2
        return max(37, 100 - (avg_pos - 1) * 3)
    try:
        pos = float(re.findall(r'\d+', pos_str)[0])
        return max(37, 100 - (pos - 1) * 3)
    except: return 43

def extract_pos(pos_str):
    if pd.isna(pos_str): return 20.0
    pos_str = str(pos_str).upper()
    if pos_str == 'DNF': return 20.0
    if 'WIN' in pos_str: return 1.0
    if pos_str == '-' or pos_str == '': return 20.0
    if '-' in pos_str:
        parts = pos_str.split('-')
        return (float(parts[0]) + float(parts[1])) / 2
    try:
        return float(re.findall(r'\d+', pos_str)[0])
    except: return 20.0

def score_driver(pred_finish, avg_finish, quali_pos, teammate_finish, has_sprint=False, avg_sprint_finish=15.0):
    # Race/Quali Points base (approximate)
    race_pts = max(37, 100 - (pred_finish - 1) * 3)
    
    # Improvement Points
    improvement = avg_finish - pred_finish
    improvement_pts = max(-10, min(10, improvement)) * 10
    
    # Overtake Points
    overtakes = quali_pos - pred_finish
    overtake_pts = overtakes * 5
    
    # Teammate Bonus
    teammate_pts = 5 if pred_finish < teammate_finish else 0
    
    total = race_pts + improvement_pts + overtake_pts + teammate_pts
    
    # Sprint Expected Points
    if has_sprint:
        # F1 GridRival generic sprint points mapping based on pos
        sprint_pts = max(0, 15 - (avg_sprint_finish - 1) * 1.5)
        total += sprint_pts
        
    return total

def fetch_active_meeting():
    """Finds the most recent or active race meeting from OpenF1"""
    try:
        year = datetime.datetime.now().year
        meetings = requests.get(f"https://api.openf1.org/v1/meetings?year={year}").json()
        if not meetings:
            meetings = requests.get(f"https://api.openf1.org/v1/meetings?year={year-1}").json()
            
        if meetings:
            return meetings[-1]['meeting_key'], year
        return 1229, 2024 # Fallback to a known 2024 meeting key
    except:
        return 1229, 2024

def calculate_e_points(drivers, teams, hist_perf, rounds):
    # 1. Fetch live OpenF1 data to build form models
    meeting_key, api_year = fetch_active_meeting()
    api_data = load_api_data(api_year, meeting_key)
    driver_mapping = fetch_driver_mapping(api_data['base_url'], meeting_key) if api_data else {}
    
    fp_pace = {} # name_acronym -> avg lap time rank
    
    # Initialize API Diagnostics Log
    api_log = {
        "timestamp": datetime.datetime.now().isoformat(),
        "meeting_key": meeting_key,
        "api_year": api_year,
        "sessions": {
            "FP1": "No Data",
            "FP2": "No Data",
            "FP3": "No Data"
        },
        "active_session_used": "None"
    }
    
    if api_data:
        # Hierarchical fetch: Try FP3 first, then FP2, then FP1
        active_session = "None"
        
        laps_data_fp3 = fetch_laps(api_data['base_url'], api_data['fp3'])
        if laps_data_fp3:
            api_log["sessions"]["FP3"] = f"Success ({len(laps_data_fp3)} laps)"
        
        laps_data_fp2 = fetch_laps(api_data['base_url'], api_data['fp2'])
        if laps_data_fp2:
            api_log["sessions"]["FP2"] = f"Success ({len(laps_data_fp2)} laps)"
            
        laps_data_fp1 = fetch_laps(api_data['base_url'], api_data['fp1'])
        if laps_data_fp1:
            api_log["sessions"]["FP1"] = f"Success ({len(laps_data_fp1)} laps)"
            
        # Determine strict fallback
        laps_data = []
        if laps_data_fp3: 
            laps_data = laps_data_fp3
            active_session = "FP3"
        elif laps_data_fp2:
            laps_data = laps_data_fp2
            active_session = "FP2"
        elif laps_data_fp1:
            laps_data = laps_data_fp1
            active_session = "FP1"
            
        api_log["active_session_used"] = active_session
        
        # Save log file
        log_path = os.path.join(BASE_DIR, "latest_api_log.json")
        try:
            with open(log_path, 'w') as f:
                json.dump(api_log, f, indent=4)
        except Exception as e:
            print(f"Error saving API log: {e}")

        if isinstance(laps_data, list):
            df_laps = pd.DataFrame(laps_data)
        else:
            df_laps = pd.DataFrame()
        
        if not df_laps.empty and 'lap_duration' in df_laps.columns and 'driver_number' in df_laps.columns:
            # Filter valid laps (excluding pit/out laps by thresholding duration > 60s and < 120s roughly)
            valid_laps = df_laps[(df_laps['lap_duration'] > 60) & (df_laps['lap_duration'] < 120)]
            medians = valid_laps.groupby('driver_number')['lap_duration'].median().sort_values()
            
            # Map position ranks using the driver acronym
            for rank, (d_num, duration) in enumerate(medians.items(), start=1):
                acronym = driver_mapping.get(d_num)
                if acronym:
                    fp_pace[acronym] = rank
    
    team_salaries = dict(zip(teams['code'], teams['salary']))
    max_team_salary = max(team_salaries.values()) if team_salaries else 1.0
    
    if not hist_perf.empty:
        hist_perf['implied_pos'] = hist_perf['race_finish'].apply(extract_pos)
        hist_perf['sprint_pos'] = hist_perf['sprint_finish'].apply(extract_pos) if 'sprint_finish' in hist_perf.columns else 20.0
        hist_perf = hist_perf.merge(rounds[['round', 'track_type']], on='round', how='left')
    
    future_rounds = rounds[rounds['round'].between(4, 9)] if not rounds.empty else pd.DataFrame([{'round':r, 'track_type': 'Unknown', 'circuit': 'Next'} for r in range(4, 10)])
    if 'has_sprint' not in future_rounds.columns:
        future_rounds['has_sprint'] = False # Default if missing
    
    predictions = []
    
    # Process drivers - Pass 1: Build Baselines
    driver_stats = {}
    for _, driver_row in drivers.iterrows():
        driver = driver_row['name']
        team_code = driver_row['code']
        # Extract practice rank dynamically using the matched acronym (team_code)
        fp_rank = fp_pace.get(team_code, 15)
        
        # Historical Support multi-year exponential smoothing
        if not hist_perf.empty:
            d_hist = hist_perf[hist_perf['driver_name'] == driver].copy()
            if not d_hist.empty and 'year' in d_hist.columns:
                weights = d_hist['year'].map({2025: 0.6, 2024: 0.3, 2023: 0.1}).fillna(0.1)
                avg_finish = np.average(d_hist['implied_pos'], weights=weights) if weights.sum() > 0 else 15.0
                
                # Sprint historical
                if 'is_sprint_weekend' in d_hist.columns:
                    sprint_hist = d_hist[d_hist['is_sprint_weekend'].isin([1, 'TRUE', True, 'Yes', '1'])]
                    if not sprint_hist.empty:
                        s_weights = sprint_hist['year'].map({2025: 0.6, 2024: 0.3, 2023: 0.1}).fillna(0.1)
                        avg_sprint_finish = np.average(sprint_hist['sprint_pos'], weights=s_weights) if s_weights.sum() > 0 else 15.0
                    else:
                        avg_sprint_finish = 15.0
                else:
                    avg_sprint_finish = 15.0
            else:
                avg_finish = d_hist['implied_pos'].mean() if not d_hist.empty else 15.0
                avg_sprint_finish = 15.0
        else:
            avg_finish = 15.0
            avg_sprint_finish = 15.0
            
        # The "Practice-to-Prediction" Logic
        # If FP_Rank >= 3 positions better than avg_finish_8, flag it
        is_improvement_candidate = (avg_finish - fp_rank) >= 3
        
        predicted_finish = avg_finish
        if is_improvement_candidate:
            predicted_finish = max(1, predicted_finish - 3)
            
        expected_quali = predicted_finish + 1
        
        driver_stats[driver] = {
            'team_code': team_code,
            'predicted_finish': predicted_finish,
            'avg_finish': avg_finish,
            'expected_quali': expected_quali,
            'avg_sprint_finish': avg_sprint_finish
        }

    # Pass 2: Calculate Teammate comparisons & Final Output
    for driver, stats in driver_stats.items():
        # Dynamic Teammate lookup
        teammates = [s['predicted_finish'] for d, s in driver_stats.items() if s['team_code'] == stats['team_code'] and d != driver]
        predicted_teammate = teammates[0] if teammates else 15.0 # Fallback
        
        for _, round_row in future_rounds.iterrows():
            r = round_row['round']
            has_sprint = str(round_row.get('has_sprint', 'FALSE')).upper() in ['1', 'TRUE', 'YES']
            
            e_points = score_driver(
                stats['predicted_finish'], 
                stats['avg_finish'], 
                stats['expected_quali'], 
                predicted_teammate,
                has_sprint,
                stats['avg_sprint_finish']
            )
            
            predictions.append({
                'Driver': driver,
                'Type': 'DRIVER',
                'Round': r,
                'E_Points': round(e_points, 1)
            })
            
    # Process Teams
    for _, team_row in teams.iterrows():
        team_code = team_row['code']
        salary = team_row['salary']
        expected_team_points = 35 + (salary / max_team_salary) * 55
        
        for _, round_row in future_rounds.iterrows():
            r = round_row['round']
            predictions.append({
                'Driver': team_row['name'],
                'Type': 'TEAM',
                'Round': r,
                'E_Points': round(expected_team_points, 1)
            })
            
    return pd.DataFrame(predictions)

def run_predictions():
    """Main entrypoint for the predictor"""
    drivers, teams, hist_perf, rounds = load_local_data()
    if drivers.empty: return []
    pred_df = calculate_e_points(drivers, teams, hist_perf, rounds)
    return pred_df.to_dict('records')

if __name__ == "__main__":
    drivers, teams, hist_perf, rounds = load_local_data()
    pred_df = calculate_e_points(drivers, teams, hist_perf, rounds)
    
    # Pivot for summary table
    summary = pred_df.pivot(index='Driver', columns='Round', values='E_Points')
    summary['Average'] = summary.mean(axis=1).round(1)
    summary = summary.sort_values(by='Average', ascending=False)
    
    print("=== Predicted Points (E_Points) for Next 4 Rounds ===")
    print(summary.to_string())
