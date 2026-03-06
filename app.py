from flask import Flask, request, jsonify, render_template, send_from_directory
import pandas as pd
import json
import os
from predictor import calculate_e_points, load_local_data
from optimizer import run_optimizer
from validator import validate_round
from flask_cors import CORS

app = Flask(__name__, static_folder=".", template_folder=".")
CORS(app) # Allow local UI to interact easily

BASE_DIR = r"c:\Users\adam\OneDrive\Documents\projects\gridrival-optimizer"

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/dashboard_data.js")
def serve_dashboard_data():
    return send_from_directory(".", "dashboard_data.js")

@app.route("/api/fetch_latest", methods=["POST"])
def fetch_latest():
    """Trigger OpenF1 data pull and predictor recalculation"""
    try:
        drivers, teams, hist_perf, rounds = load_local_data()
        pred_df = calculate_e_points(drivers, teams, hist_perf, rounds)
        
        # Save updated predictions
        pred_df.to_csv(os.path.join(BASE_DIR, "latest_predictions.csv"), index=False)
        return jsonify({"status": "success", "message": "Predictions updated from OpenF1"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/run_optimization", methods=["POST"])
def run_optimization():
    """Run the optimizer algorithm for teams"""
    # For now, this returns the mock JSON structure representing an optimization result
    
    drivers, teams, hist_perf, rounds = load_local_data()
    
    # Recombine drivers and teams since run_optimizer expects both together
    if not drivers.empty and not teams.empty:
        drivers_teams = pd.concat([drivers, teams], ignore_index=True)
    else:
        drivers_teams = pd.DataFrame()
        
    # Load user defined teams if they exist
    teams_path = os.path.join(BASE_DIR, "user_teams.json")
    user_teams = []
    if os.path.exists(teams_path):
        try:
            with open(teams_path, "r") as f:
                user_teams = json.load(f)
        except:
            pass
            
    results = []
    gammas = [2.0, 1.0, 0.5, 0.0]
    
    # Process user teams or simulate default 4 teams
    if user_teams and isinstance(user_teams, list):
        for i, t_data in enumerate(user_teams):
            rows = []
            lengths = t_data.get('lengths', {})
            
            if t_data.get('constructor'):
                c_name = t_data['constructor']
                rows.append({'name': c_name, 'length_remaining': lengths.get(c_name, 1)})
                
            for d in t_data.get('drivers', []):
                if d:
                    rows.append({'name': d, 'length_remaining': lengths.get(d, 1)})
            
            ct_df = pd.DataFrame(rows)
            # Default to balanced bias for user teams
            r = run_optimizer(drivers_teams, hist_perf, ct_df, start_round=4, horizon=5, GAMMA=1.0)
            if r and 'error' not in r:
                r['team_id'] = t_data.get('name', f"Team {i+1}")
                results.append(r)
            elif r and 'error' in r:
                print(f"Error in optimization {i}: {r['error']}")
    else:
        # Simulate processing 4 teams
        for i in range(4):
            # We pass empty DataFrame for current_team to simulate raw generation
            r = run_optimizer(drivers_teams, hist_perf, pd.DataFrame(), start_round=4, horizon=5, GAMMA=gammas[i])
            if r and 'error' not in r:
                # Tag the result with a team name for UI rendering
                r['team_id'] = f"Team {i+1}"
                results.append(r)
            elif r and 'error' in r:
                print(f"Error in optimization {i}: {r['error']}")
            
    # Save to JS file to avoid CORS issues on local UI, acting as a cache
    out_path = os.path.join(BASE_DIR, 'dashboard_data.js')
    with open(out_path, 'w') as f:
        f.write("const dashboardData = ")
        json.dump(results, f, indent=2)
        f.write(";")
        
    return jsonify({"status": "success", "data": results})

@app.route("/api/validate", methods=["POST"])
def validate_action():
    """Trigger the validation checker"""
    # Load recent predictions to compare against
    # Assuming predictions are exported after `fetch_latest`
    pred_path = os.path.join(BASE_DIR, "latest_predictions.csv")
    if not os.path.exists(pred_path):
         return jsonify({"status": "error", "message": "No recent predictions to validate."}), 400
         
    pred_df = pd.read_csv(pred_path)
    # create mapping
    pred_pts_dict = dict(zip(pred_df['Driver'], pred_df['E_Points']))
    
    # We don't have predicted sal natively output from predictor.py alone yet, standardizing dict
    pred_sal_dict = {} 
    
    log = validate_round(pred_pts_dict, pred_sal_dict)
    
    return jsonify({"status": "success", "log": log})


@app.route("/api/get_races", methods=["GET"])
def get_races():
    """Returns a list of all races."""
    _, _, _, rounds = load_local_data()
    races = []
    if not rounds.empty:
        races = rounds[['round', 'race_name', 'circuit', 'country', 'date_start']].to_dict('records')
    return jsonify({"status": "success", "races": races})

@app.route("/api/get_race_data/<int:round_id>", methods=["GET"])
def get_race_data(round_id):
    """Returns the downloaded API prediction data specific to a round."""
    pred_path = os.path.join(BASE_DIR, "latest_predictions.csv")
    if not os.path.exists(pred_path):
        return jsonify({"status": "success", "data": []}) # No active dataset at all
        
    pred_df = pd.read_csv(pred_path)
    if pred_df.empty or 'Round' not in pred_df.columns:
        return jsonify({"status": "success", "data": []})
        
    # Filter by the requested round
    round_data = pred_df[pred_df['Round'] == round_id]
    
    # Send empty array if missing
    return jsonify({"status": "success", "data": round_data.to_dict('records')})

@app.route("/api/get_log", methods=["GET"])
def get_log():
    """Returns the API connection log diagnostics"""
    log_path = os.path.join(BASE_DIR, "latest_api_log.json")
    if os.path.exists(log_path):
        with open(log_path, 'r') as f:
            data = json.load(f)
        return jsonify({"status": "success", "log": data})
    else:
        return jsonify({"status": "success", "log": {
            "timestamp": "N/A",
            "meeting_key": "N/A",
            "api_year": "N/A",
            "active_session_used": "None",
            "sessions": {
                "FP1": "No Data (Run Fetch Latest Info)",
                "FP2": "No Data",
                "FP3": "No Data"
            }
        }})

@app.route("/api/save_teams", methods=["POST"])
def save_teams():
    data = request.json
    teams_path = os.path.join(BASE_DIR, "user_teams.json")
    with open(teams_path, "w") as f:
        json.dump(data, f, indent=2)
    return jsonify({"status": "success", "message": "Teams saved successfully"})

@app.route("/api/get_roster", methods=["GET"])
def get_roster():
    drivers, teams, _, _ = load_local_data()
    roster = []
    if not drivers.empty:
        roster.extend(drivers.to_dict('records'))
    if not teams.empty:
        roster.extend(teams.to_dict('records'))
    return jsonify({"status": "success", "roster": roster})

@app.route("/api/save_roster", methods=["POST"])
def save_roster():
    data = request.json # expected dict with 'roster' key
    if not data or 'roster' not in data:
        return jsonify({"status": "error", "message": "Invalid data format"}), 400
        
    df = pd.DataFrame(data['roster'])
    required_cols = ['type', 'name', 'code', 'salary', 'round', 'points']
    for col in required_cols:
        if col not in df.columns:
            df[col] = 0 if col in ['salary', 'round', 'points'] else ''
            
    # Ensure correct column order
    df = df[required_cols]
            
    csv_path = os.path.join(BASE_DIR, "GridRivals - drivers and teams.csv")
    df.to_csv(csv_path, index=False)
    return jsonify({"status": "success", "message": "Roster updated successfully"})

@app.route("/api/get_historical_track/<int:round_id>", methods=["GET"])
def get_historical_track(round_id):
    _, _, hist_perf, rounds = load_local_data()
    
    if rounds.empty or hist_perf.empty:
        return jsonify({"status": "success", "data": []})
        
    round_info = rounds[rounds['round'] == round_id]
    if round_info.empty:
        return jsonify({"status": "success", "data": []})
        
    track_type = round_info.iloc[0]['track_type']
    
    hist_perf_merged = hist_perf.merge(rounds[['round', 'track_type']], on='round', how='left')
    filtered_hist = hist_perf_merged[hist_perf_merged['track_type'] == track_type]
    
    # Sort & Filter to 3 years max
    if not filtered_hist.empty:
        if 'year' in filtered_hist.columns:
            filtered_hist = filtered_hist.sort_values(by=['year', 'round', 'driver_name'], ascending=[False, True, True])
        else:
            filtered_hist = filtered_hist.sort_values(by=['round', 'driver_name'])
    
    # Clean up empty notes (replace NaN with empty string)
    filtered_hist = filtered_hist.fillna('')
    
    return jsonify({"status": "success", "track_type": track_type, "data": filtered_hist.to_dict('records')})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
