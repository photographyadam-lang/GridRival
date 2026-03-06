# GridRival Optimizer

A mathematically rigorous multi-period portfolio optimizer designed to build perfect fantasy racing rosters for GridRival.

## Core Features
1. **Live OpenF1 API Ingestion**: Dynamically pulls real-time driver pace from Free Practice 1, 2, and 3, seamlessly connecting lap times to expected performance algorithms.
2. **Multi-Year Exponential Smoothing**: Projects expected baseline performance by actively weighting recent finishes (2025/2024) drastically higher than legacy finishes (2023).
3. **Automated Sprint Processing**: Projects elevated points for "sprint specialist" drivers whenever the calendar detects a future sprint weekend.
4. **Early Season Contract Uncertainty Penalty**: Discourages the optimizer from signing inflexible 3-5 race deals early in the season (Rounds 1-7), actively mitigating real-world car development risk.
5. **Linear Programming (PuLP)**: Actively generates 5-race strategic roadmaps covering team selections, talent driver allocations, and cascading budget/salary manipulations for up to 4 distinct rosters.
6. **Live Diagnostics Log**: Produces real-time transparency readouts guaranteeing the user knows exactly what Free Practice session is powering the math.

## Application Architecture

The project consists of three critical layers:
- **`predictor.py`**: The mathematical forecasting engine. Scrapes the OpenF1 `/drivers` and `/laps` endpoints to map physical cars to GridRival acronyms. Outputs expected points (`E_Points`).
- **`optimizer.py`**: The strategic brain. Models GridRival's unique "salary smoothing" formula ($\Delta_{raw}$ rounding to $0.1m$, clamped at $\pm 2.0m$) and solves the roster combinatorials using `pulp`.
- **`app.py` / `index.html`**: A lightweight Flask backend and React-style responsive static dashboard that powers the User Interface.

## How to Run

1. Open your terminal and start the Flask backend server:
```bash
python app.py
```
2. The UI will automatically be hosted locally (usually at `http://127.0.0.1:5000`).
3. Click **Fetch Latest F1 Data** to instruct the predictor to sweep the OpenF1 APIs for Free Practice data.
4. Click **Run Optimization (All Teams)** to generate optimal mathematical rosters.
5. Optionally, use the "Global Roster Editor" to manually synchronize driver salaries, or the "API Diagnostics Log" to view your data health.

## Ongoing Validation

The project is backed by an active 11-function Pytest framework. To ensure structural integrity before making major logic changes, execute the suite:
```bash
python -m pytest tests/
```
