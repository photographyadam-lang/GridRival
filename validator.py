import pandas as pd
import os

BASE_DIR = r"c:\Users\adam\OneDrive\Documents\projects\gridrival-optimizer"

def validate_round(predicted_pts_dict, predicted_sal_dict, actual_data_path=None):
    """
    Compares predicted points and salaries vs actuals derived from GridRivals - drivers and teams.csv
    predicted_pts_dict: dict mapping 'entity_name' -> pred_pts
    predicted_sal_dict: dict mapping 'entity_name' -> pred_salary
    """
    if actual_data_path is None:
        actual_data_path = os.path.join(BASE_DIR, "GridRivals - drivers and teams.csv")
        
    try:
        actuals = pd.read_csv(actual_data_path)
    except FileNotFoundError:
        print(f"Validation skipped. Could not find actuals data at {actual_data_path}")
        return
        
    log_rows = []
    
    for _, row in actuals.iterrows():
        entity = row['name']
        actual_pts = row.get('total_points', 0) # Assumes overall points for simplicity or round points if available
        actual_salary = row.get('salary', 0)
        code = row.get('code', entity)
        
        pred_pts = predicted_pts_dict.get(entity, 0)
        pred_sal = predicted_sal_dict.get(entity, actual_salary) # Default to actual if no pred found
        
        pts_diff = round(actual_pts - pred_pts, 1) if pred_pts else 0
        sal_diff = round(actual_salary - pred_sal, 1) if pred_sal else 0
        
        logic_flag = "OK"
        if pts_diff != 0:
            logic_flag = "SCORING_MISMATCH"
        if sal_diff != 0 and logic_flag != "SCORING_MISMATCH":
            logic_flag = "SALARY_DRIFT"
        elif sal_diff != 0:
            logic_flag = "SCORING_MISMATCH & SALARY_DRIFT"
            
        # In a real scenario, actual points should map specifically to the current round. 
        # Here we mock it by checking total vs expected for demo purposes.
        
        log_rows.append({
            'element_id': code,
            'pred_pts': pred_pts,
            'actual_pts': actual_pts,
            'pts_diff': pts_diff,
            'pred_salary': pred_sal,
            'actual_salary': actual_salary,
            'sal_diff': sal_diff,
            'logic_flag': logic_flag
        })
        
    log_df = pd.DataFrame(log_rows)
    out_path = os.path.join(BASE_DIR, "validation_log.csv")
    log_df.to_csv(out_path, index=False)
    print(f"Validation complete. Log saved to {out_path}")
    
    return log_df.to_dict('records')

if __name__ == "__main__":
    # Mock validation run
    print("Running mock validation...")
    validate_round({}, {})
