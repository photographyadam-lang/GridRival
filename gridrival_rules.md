<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# stitch everything (drivers, constructors, contracts, salaries) into a single top‑to‑bottom `GridRival_F1_Rules.md` so i can just paste it into Gemini.

```markdown
# GridRival F1 – Contracts Game Rules (Full Technical Spec)

This document describes the **GridRival F1 Contracts fantasy game** in a way that an optimizer or rules engine can consume. It covers roster structure, contracts, driver and constructor scoring, and the salary‑adjustment system.

---

## 1. Game structure and objective

- **Game mode:** F1 **Contracts** league.
- **Objective:** Maximize **season‑long fantasy points** by signing drivers and one constructor to contracts, subject to a salary‑cap budget and contract rules.
- **Reality basis:** All fantasy points are derived from **official F1 results** (qualifying, sprint, and race), including post‑race penalties and classification changes.

---

## 2. Roster, elements, and budget

### 2.1 Roster composition

- Total roster slots: **6**
  - **5 driver** slots.
  - **1 constructor** slot.
- It is allowed to field **fewer than 6 elements**, but if any slot is empty you are **not eligible** to designate a **Talent Driver** (double‑points driver) for that event.

### 2.2 Budget

- Initial team budget: **$100,000,000** (fantasy money, unit choice is arbitrary for modeling).
- Every roster element (driver or constructor) has a **salary**:
  - `salary(e, t)` = salary of element `e` before event `t`.

### 2.3 Salaries and portfolio adjustment on release

- Salaries reflect GridRival’s estimate of an element’s **future fantasy performance**.
- Salaries change over time via the salary‑adjustment algorithm (section 7).
- When you **release** an element `e`:
  - Let `salary_sign(e)` be the salary when you originally signed `e`.
  - Let `salary_current(e)` be the salary at the time you release `e`.
  - Budget is adjusted by the difference:
    ```text
    budget_new = budget_old + (salary_current(e) - salary_sign(e))
    ```
  - If `salary_current > salary_sign` → you gain budget.
  - If `salary_current < salary_sign` → you lose budget.

### 2.4 Team value and possible floor

Define:

```text
team_value = budget + sum_current_salaries(all roster elements)
```

GridRival guidance mentions a **team value floor** to stop team value collapsing too far. For modeling, you can allow a parameter:

```text
TEAM_VALUE_FLOOR (optional)
team_value = max(team_value, TEAM_VALUE_FLOOR)
```

If you don’t have an explicit floor from rules, you can disable this.

---

## 3. Contracts

### 3.1 Contract length

When signing any element `e`, you must choose a **contract length** in races:

```text
CONTRACT_MIN_RACES = 1
CONTRACT_MAX_RACES = 5
1 <= contract_length(e) <= 5
```

- `contract_remaining(e)` decrements by 1 after each relevant race.


### 3.2 Contract expiry

- When `contract_remaining(e)` reaches **0**, the contract **expires**:
    - `e` is removed from the roster.
    - The roster slot becomes empty until you sign a new element.


### 3.3 Early release and re‑sign (model hooks)

The app UX implies early release and possible re‑sign constraints; the exact numbers are not visible in the screenshots. For an optimizer, you can parameterize:

```text
EARLY_RELEASE_ALLOWED        = true/false
EARLY_RELEASE_PENALTY_MODE   = "none" | "flat" | "percentage_of_salary" | "remaining_length_scaled"
EARLY_RELEASE_PENALTY_VALUE  = numeric parameter
RE_SIGN_COOLDOWN_RACES      = integer (e.g., 0 if no cooldown)
```

Then:

- If early release is allowed and used, subtract `penalty(e)` from budget according to the chosen mode.
- Prevent re‑signing the same element until `RE_SIGN_COOLDOWN_RACES` events have elapsed after release, if cooldown > 0.

You can set these based on the full text of the GridRival help center if you want exact behavior; this spec simply exposes the hooks.

---

## 4. Talent Driver

### 4.1 Definition

- A **Talent Driver** is one of your roster drivers whose **event points are doubled**.


### 4.2 Eligibility rule

- You may select a Talent Driver **only if your roster is full** (5 drivers + 1 constructor all filled before lock).
- If any slot is empty, you **cannot** designate a Talent Driver for that event.


### 4.3 Scoring transform

For each event:

- Let `P_driver(d)` be the total fantasy points of driver `d` from all driver scoring components (section 5), **before** Talent Driver multipliers.
- Let `talent(d)` = 1 if `d` is the chosen Talent Driver, else 0.

Then:

```text
P_driver_final(d) = P_driver(d) * (2 if talent(d) == 1 else 1)
```

Team total points for the event use `P_driver_final(d)`.

---

## 5. Driver scoring – full specification

For each driver `d` at each event `t`:

```text
P_driver(d) =
    RACE_FINISH_POINTS(d)
  + SPRINT_FINISH_POINTS(d)
  + QUALIFYING_POINTS(d)
  + OVERTAKE_POINTS(d)
  + IMPROVEMENT_POINTS(d)
  + BEATING_TEAMMATE_POINTS(d)
  + COMPLETION_POINTS(d)
```


### 5.1 Race finish position – driver points

`race_position(d)` = final classified race position (1–22).

```text
RACE_FINISH_TABLE:
  1st  -> 100
  2nd  -> 97
  3rd  -> 94
  4th  -> 91
  5th  -> 88
  6th  -> 85
  7th  -> 82
  8th  -> 79
  9th  -> 76
  10th -> 73
  11th -> 70
  12th -> 67
  13th -> 64
  14th -> 61
  15th -> 58
  16th -> 55
  17th -> 52
  18th -> 49
  19th -> 46
  20th -> 43
  21st -> 40
  22nd -> 37
```

Computation:

```text
RACE_FINISH_POINTS(d) = RACE_FINISH_TABLE[ race_position(d) ]
```

(If the driver is not classified or DSQ, use whatever mapping the platform applies to give them a final “position”.)

---

### 5.2 Sprint finish position – driver points

`sprint_position(d)` = final classified sprint position (1–22). If there is no sprint, `SPRINT_FINISH_POINTS(d) = 0`.

```text
SPRINT_FINISH_TABLE:
  1st  -> 22
  2nd  -> 21
  3rd  -> 20
  4th  -> 19
  5th  -> 18
  6th  -> 17
  7th  -> 16
  8th  -> 15
  9th  -> 14
  10th -> 13
  11th -> 12
  12th -> 11
  13th -> 10
  14th -> 9
  15th -> 8
  16th -> 7
  17th -> 6
  18th -> 5
  19th -> 4
  20th -> 3
  21st -> 2
  22nd -> 1
```

Computation:

```text
SPRINT_FINISH_POINTS(d) =
    0                                        if no sprint at event
    SPRINT_FINISH_TABLE[ sprint_position(d) ] otherwise
```


---

### 5.3 Qualifying finish position – driver points

Qualifying points are based on **qualifying position**, not grid start position (grid penalties do not affect these points).

`quali_position(d)` = official qualifying result (1–22).

```text
QUALI_POINTS_TABLE:
  1st  -> 50
  2nd  -> 48
  3rd  -> 46
  4th  -> 44
  5th  -> 42
  6th  -> 40
  7th  -> 38
  8th  -> 36
  9th  -> 34
  10th -> 32
  11th -> 30
  12th -> 28
  13th -> 26
  14th -> 24
  15th -> 22
  16th -> 20
  17th -> 18
  18th -> 16
  19th -> 14
  20th -> 12
  21st -> 10
  22nd -> 8
```

Computation:

```text
QUALIFYING_POINTS(d) = QUALI_POINTS_TABLE[ quali_position(d) ]
```


---

### 5.4 Overtake points (net positions gained)

Overtake points reward **net positions gained** from qualifying to race.

```text
delta_pos(d) = quali_position(d) - race_position(d)
```

- `delta_pos(d) > 0` → positions gained.
- `delta_pos(d) = 0` → no net change.
- `delta_pos(d) < 0` → positions lost.

From the scoring screen:

```text
OVERTAKE_POINTS_PER_POSITION_GAINED = +3
```

No negative values or caps are shown, so by default:

```text
if delta_pos(d) > 0:
    OVERTAKE_POINTS(d) = delta_pos(d) * 3
else:
    OVERTAKE_POINTS(d) = 0
```

If the live rules specify penalties for lost positions or a cap, adjust accordingly.

---

### 5.5 Improvement Points (vs 8‑race rolling average)

Improvement Points reward finishing better than a driver’s recent performance.

For event `t`:

1. Compute 8‑race average finish:

```text
avg_finish_8(d, t) = average( race_position(d, t-1), ..., race_position(d, t-8) )
avg_rounded(d, t)  = ceil( avg_finish_8(d, t) )
```

2. Determine how many positions the driver beat this average by:

```text
positions_improved(d, t) = max(0, avg_rounded(d, t) - race_position(d, t))
```

3. Apply the Improvement Points table from the app:

```text
IMPROVEMENT_POINTS_TABLE (positions_improved -> points):
  1  -> 0
  2  -> 2
  3  -> 4
  4  -> 6
  5  -> 9
  6  -> 12
  7  -> 16
  8  -> 20
  9  -> 25
  10 -> 30
  11 -> 30
  12 -> 30
  13 -> 30
  14 -> 30
  15 -> 30
  16 -> 30
  17 -> 30
  18 -> 30
  19 -> 30
  20 -> 30
  21 -> 30
  22 -> 30
```

4. Computation:

```text
IMPROVEMENT_POINTS(d) = IMPROVEMENT_POINTS_TABLE[ positions_improved(d, t) ]
```


---

### 5.6 Beating Teammate Points (margin‑based)

Beating‑teammate points depend on how many positions the winning teammate finishes ahead by.

For a constructor with race drivers `d1` and `d2`:

```text
margin = | race_position(d1) - race_position(d2) |
```

Points table from the app:

```text
WIN_MARGIN (positions)   POINTS TO WINNER
1–3                       2
4–7                       5
8–12                      8
13+                       12
```

Computation:

```text
if race_position(d1) < race_position(d2):
    winner = d1
    loser  = d2
else if race_position(d2) < race_position(d1):
    winner = d2
    loser  = d1
else:
    // same classified position → no teammate bonus
    BEATING_TEAMMATE_POINTS(d1) = 0
    BEATING_TEAMMATE_POINTS(d2) = 0

if race_position(d1) != race_position(d2):
    m = margin
    if 1 <= m <= 3:
        pts = 2
    else if 4 <= m <= 7:
        pts = 5
    else if 8 <= m <= 12:
        pts = 8
    else:   // m >= 13
        pts = 12

    BEATING_TEAMMATE_POINTS(winner) = pts
    BEATING_TEAMMATE_POINTS(loser)  = 0
```


---

### 5.7 Completion Points (race distance completed)

Completion points reward staying in the race.

From the app:

- 25% distance: 3 points.
- 50% distance: 3 points.
- 75% distance: 3 points.
- 90% distance: 3 points.

Let:

- `TOTAL_LAPS` = scheduled race distance.
- `last_lap_completed(d)` = last lap actually completed by driver `d`.

GridRival “divides the number of laps by these percentages and rounds down to the nearest lap.” So:

```text
lap_25 = floor(TOTAL_LAPS * 0.25)
lap_50 = floor(TOTAL_LAPS * 0.50)
lap_75 = floor(TOTAL_LAPS * 0.75)
lap_90 = floor(TOTAL_LAPS * 0.90)
```

Then:

```text
COMPLETION_POINTS(d) =
    (last_lap_completed(d) >= lap_25 ? 3 : 0) +
    (last_lap_completed(d) >= lap_50 ? 3 : 0) +
    (last_lap_completed(d) >= lap_75 ? 3 : 0) +
    (last_lap_completed(d) >= lap_90 ? 3 : 0)
```


---

## 6. Constructor scoring – full specification

For each constructor `C` at each event:

```text
P_constructor(C) =
    CONSTRUCTOR_QUALI_POINTS(C)
  + CONSTRUCTOR_RACE_POINTS(C)
```


### 6.1 Constructor qualifying points

`constructor_quali_position(C)` = constructor’s qualifying position (1–22) as displayed in the “Constructors → Qualifying Points” panel.

```text
CONSTRUCTOR_QUALI_POINTS_TABLE:
  1st  -> 30
  2nd  -> 29
  3rd  -> 28
  4th  -> 27
  5th  -> 26
  6th  -> 25
  7th  -> 24
  8th  -> 23
  9th  -> 22
  10th -> 21
  11th -> 20
  12th -> 19
  13th -> 18
  14th -> 17
  15th -> 16
  16th -> 15
  17th -> 14
  18th -> 13
  19th -> 12
  20th -> 11
  21st -> 10
  22nd -> 9
```

Computation:

```text
CONSTRUCTOR_QUALI_POINTS(C) =
    CONSTRUCTOR_QUALI_POINTS_TABLE[ constructor_quali_position(C) ]
```

*(The app itself determines `constructor_quali_position(C)` from driver results; an optimizer can treat that position as input.)*

---

### 6.2 Constructor race points

`constructor_race_position(C)` = constructor’s race position (1–22) as displayed in the “Constructors → Race Points” panel.

```text
CONSTRUCTOR_RACE_POINTS_TABLE:
  1st  -> 60
  2nd  -> 58
  3rd  -> 56
  4th  -> 54
  5th  -> 52
  6th  -> 50
  7th  -> 48
  8th  -> 46
  9th  -> 44
  10th -> 42
  11th -> 40
  12th -> 38
  13th -> 36
  14th -> 34
  15th -> 32
  16th -> 30
  17th -> 28
  18th -> 26
  19th -> 24
  20th -> 22
  21st -> 20
  22nd -> 18
```

Computation:

```text
CONSTRUCTOR_RACE_POINTS(C) =
    CONSTRUCTOR_RACE_POINTS_TABLE[ constructor_race_position(C) ]
```


---

## 7. Salary system – default tables and adjustment algorithm

GridRival provides base salary tables for drivers and constructors and dynamically adjusts salaries after each event based on fantasy performance.

### 7.1 Default driver salary table

`DEFAULT_DRIVER_SALARY_RANK_TABLE[rank]` (values in £, as shown in the app):

```text
Rank 1  -> £34,000,000
Rank 2  -> £32,400,000
Rank 3  -> £30,800,000
Rank 4  -> £29,200,000
Rank 5  -> £27,600,000
Rank 6  -> £26,000,000
Rank 7  -> £24,400,000
Rank 8  -> £22,800,000
Rank 9  -> £21,200,000
Rank 10 -> £19,600,000
Rank 11 -> £18,000,000
Rank 12 -> £16,400,000
Rank 13 -> £14,800,000
Rank 14 -> £13,200,000
Rank 15 -> £11,600,000
Rank 16 -> £10,000,000
Rank 17 -> £8,400,000
Rank 18 -> £6,800,000
Rank 19 -> £5,200,000
Rank 20 -> £3,600,000
Rank 21 -> £2,000,000
Rank 22 -> £400,000
```


### 7.2 Default constructor salary table

`DEFAULT_CONSTRUCTOR_SALARY_RANK_TABLE[rank]` (from the app; extend if more ranks appear):

```text
Rank 1  -> £30,000,000
Rank 2  -> £27,400,000
Rank 3  -> £24,800,000
Rank 4  -> £22,200,000
Rank 5  -> £19,600,000
Rank 6  -> £17,000,000
Rank 7  -> £14,400,000
Rank 8  -> £11,800,000
Rank 9  -> £9,200,000
Rank 10 -> £6,600,000
Rank 11 -> £4,000,000
```

If the app shows ranks 12–22, add them in the same form.

### 7.3 Salary adjustment algorithm

This applies separately to drivers and constructors but uses the same logic.

Definitions:

- `S_before(e)` = salary of element `e` **before** the event.
- `rank_event(e)` = **fantasy points rank** for the event (1 = most points among drivers or constructors of that type, 22 = least).
- For drivers: `DEFAULT_S(rank)` = `DEFAULT_DRIVER_SALARY_RANK_TABLE[rank]`.
- For constructors: `DEFAULT_S(rank)` = `DEFAULT_CONSTRUCTOR_SALARY_RANK_TABLE[rank]`.


#### Step 1 – Rank by event fantasy points

After each event:

```text
rank_event(e) = rank of e by fantasy points within its type (driver/constructor).
```


#### Step 2 – Compute base salary variation

From the in‑app description:

> “Salary variation is the difference between a driver or constructor’s salary before the race, to the salary associated with their fantasy rank after the race using the salary shown on the default salary table.”

So:

```text
BASE_VARIATION(e) = DEFAULT_S( rank_event(e) ) - S_before(e)
```

Example from app:

- S_before = £15.8M
- rank_event = 8 → DEFAULT_S(8) = £22.8M
- BASE_VARIATION = 22.8M − 15.8M = +£7.0M


#### Step 3 – Scale, round, clamp, update

From the app:

> “We divide the base salary variation by 4 and round down to the nearest 100k to determine the final adjustment amount. The maximum increase is ±£2M for drivers, ±£3M for constructors and the minimum adjustment is ±£100k for both.”

Constants:

```text
DRIVER_MAX_ADJUST_UP   = +£2,000,000
DRIVER_MAX_ADJUST_DOWN = -£2,000,000

CONSTR_MAX_ADJUST_UP   = +£3,000,000
CONSTR_MAX_ADJUST_DOWN = -£3,000,000

MIN_ABS_ADJUST         = £100,000
```

Algorithm:

```text
ADJUST_RAW(e) = BASE_VARIATION(e) / 4
```

Round toward zero to the nearest £100k:

```text
abs_raw = abs(ADJUST_RAW(e))
abs_rounded = floor(abs_raw / 100,000) * 100,000
ADJUST_ROUNDED(e) = sign(ADJUST_RAW(e)) * abs_rounded
```

Enforce minimum absolute adjustment (if non‑zero):

```text
if ADJUST_ROUNDED(e) != 0 and abs(ADJUST_ROUNDED(e)) < MIN_ABS_ADJUST:
    ADJUST_ROUNDED(e) = sign(ADJUST_ROUNDED(e)) * MIN_ABS_ADJUST
```

Clamp based on type:

```text
if e is driver:
    ADJUST_CLAMPED(e) = min( max(ADJUST_ROUNDED(e), DRIVER_MAX_ADJUST_DOWN),
                             DRIVER_MAX_ADJUST_UP )
else if e is constructor:
    ADJUST_CLAMPED(e) = min( max(ADJUST_ROUNDED(e), CONSTR_MAX_ADJUST_DOWN),
                             CONSTR_MAX_ADJUST_UP )
```

Final salary:

```text
S_after(e) = S_before(e) + ADJUST_CLAMPED(e)
```

Example from the app’s “Salary Adjustment Example”:

- S_before = £15.8M
- rank_event = 8 → DEFAULT_S(8) = £22.8M
- BASE_VARIATION = +£7.0M
- ADJUST_RAW = 7.0M / 4 = 1.75M → rounded to £1.7M
- Within ±£2M and ≥ £100k → ADJUST_CLAMPED = +£1.7M
- `S_after = 15.8M + 1.7M = 17.5M`


### 7.4 Initial season salaries

Per the in‑app description:

- All elements start the season with **manually set starting salaries** based on previous season performance, pre‑season testing, and projected performance.
- For modeling, treat these `S_start(e)` values as **given inputs** for round 1; then update them after each event using the algorithm above.

---

## 8. Team event score and season total

For a team `T` at event `E`:

```text
TEAM_EVENT_SCORE_RAW(E, T) =
    sum_over_roster_drivers( P_driver_final(d) ) +
    P_constructor(C)
```

If GridRival enforces a **minimum event score** (e.g., 650 points) you can apply:

```text
MIN_EVENT_SCORE = 650  // if confirmed
TEAM_EVENT_SCORE(E, T) = max(MIN_EVENT_SCORE, TEAM_EVENT_SCORE_RAW(E, T))
```

Season total is the sum of `TEAM_EVENT_SCORE(E, T)` over all completed events.

---

This `GridRival_F1_Rules.md` file is structured so another model (e.g., Gemini) can convert each section directly into code: ingest F1 data, compute driver and constructor scores, apply Talent Driver multipliers, update salaries, and optimize contracts subject to budget and roster rules.

```
```

