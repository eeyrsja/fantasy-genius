### Formal Specification — `select_initial_squad`

---

#### 1  Purpose

Construct an **initial 15-player Fantasy Premier League squad** that maximises **expected FPL points for Game-weeks 1 – 4** while obeying all official constraints (budget, position quotas, club limit). Optimisation must be reproducible and support swapping-in alternative scoring/forecast models.

---

#### 2  External References

Official 2025/26 FPL rules: 15 players = 2 GK + 5 DEF + 5 MID + 3 FWD; £100 m budget; ≤ 3 players per Premier-League club. ([FourFourTwo][1])

---

#### 3  Function Signature

```python
def select_initial_squad(
    players: pd.DataFrame,
    fixtures: pd.DataFrame,
    *,
    gw_start: int = 1,
    gw_end: int = 4,
    budget_million: float = 100.0,
    solver: str | None = "mip",
    expected_points_cols: Sequence[str] | None = None,
    custom_constraints: dict | None = None,
) -> "SquadResult":
    ...
```

`SquadResult` is a frozen `@dataclass`:

```python
@dataclass(frozen=True)
class SquadResult:
    squad_df: pd.DataFrame         # 15 rows, same columns as input + 'position'
    total_cost: float              # £m
    expected_points: float         # sum over GW range
    per_position: dict[str, list]  # e.g. {"GK": [id1, id2], ...}
    club_counts: dict[int, int]    # {team_code: n}
    objective_details: dict        # diagnostics from solver
```

---

#### 4  Input Contracts

| Name       | Type           | Required Columns / Schema                                                                                                                                                                                                                             |
| ---------- | -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `players`  | `pd.DataFrame` | `id`, `element_type`, `team`, `now_cost` (int, £0.1 m units) plus **either**:<br> (a) per-GW expected points cols – default naming `ep_gw{n}`; **or**<br> (b) raw stats; in that case caller must supply `expected_points_cols` generated previously. |
| `fixtures` | `pd.DataFrame` | `event` (GW int), `team_h`, `team_a`, `team_h_difficulty`, `team_a_difficulty` (1 = easiest … 5 = hardest). Additional columns are ignored.                                                                                                           |

Assumptions

* `players` covers the active player pool and is **≤ 1 000 rows**.
* Costs in API units (e.g. 45 = £4.5 m).
* Difficulty ratings align with FPL scale.

---

#### 5  Processing Steps

1. **Validation**

   * Confirm required columns present and unique player `id`.
   * Verify cost & GW range consistency.
   * Validate constraints and raise `ValueError` for breach.

2. **Expected-Points Vector**

   * If `expected_points_cols` is `None`, derive column names `ep_gw{gw_start} … ep_gw{gw_end}`.
   * Aggregate:

     ```python
     players["exp_pts_window"] = players[expected_points_cols].sum(axis=1)
     ```

3. **Optimisation Model**

   * Decision variables: `x_i ∈ {0,1}` for each player `i`.
   * Objective: **maximise** `Σ x_i * exp_pts_window_i`.
   * Constraints:

     | Description     | Formal Expression                             |
     | --------------- | --------------------------------------------- |
     | Squad size      | `Σ x_i = 15`                                  |
     | Position quotas | `Σ_{i∈GK} x_i = 2`, `Σ_{i∈DEF} x_i = 5`, etc. |
     | Budget          | `Σ x_i * now_cost_i ≤ budget_million * 10`    |
     | Club limit      | `∀ club c: Σ_{i∈c} x_i ≤ 3`                   |
   * Solver back-ends:

     * `"mip"` (default) → **Mixed Integer Linear Programming** via OR-Tools / PuLP.
     * `"ga"` → genetic algorithm (fallback; slower but no external libs).
     * Custom solver accepted via `solver` callable.

4. **Post-processing**

   * Build `SquadResult`; compute `per_position` and `club_counts`.
   * If solver reports multiple optima, choose the one with **lowest total cost** (keeps bank).

5. **Error Handling**

   * Infeasible problem → raise `InfeasibleError` detailing violated constraint(s).
   * Missing data → `KeyError` with column list.

---

#### 6  Performance Requirements

* Run time less than a hour on i7 PC with 32 GB RAM.

---

#### 7  Extensibility Hooks

| Hook                 | Purpose                                                               |
| -------------------- | --------------------------------------------------------------------- |
| `custom_constraints` | Dict specifying additional linear constraints, e.g. “≥ 1 £4.0 m DEF”. |
| Alternate objective  | Provide callable `objective_fn(players, x)` to replace default.       |
| Solver pluggability  | Pass object with `build_model(players, constraints) -> solve()`.      |

---

#### 8  Unit-Test Matrix (minimum)

| Case | Variation                                        | Expected Outcome               |
| ---- | ------------------------------------------------ | ------------------------------ |
| 1    | Valid minimal dataset (20 players)               | Feasible, returns 15-row squad |
| 2    | Budget too low (`budget_million=50`)             | `InfeasibleError`              |
| 3    | >3 players same club in input without duplicates | Solver should respect limit    |
| 4    | Missing `element_type` column                    | `KeyError`                     |
| 5    | Tied optimal points, different costs             | Chooses cheaper squad          |

---

#### 9  Out-of-Scope for V1

* Captain / vice-captain selection
* Bench order optimisation
* Transfer strategy beyond GW4
* Chips usage (Bench Boost, Free Hit, etc.)

---

This specification is ready for implementation. Let me know when you want the scaffold code or adjustments.

[1]: https://www.fourfourtwo.com/features/fpl-what-is-fantasy-premier-league-and-how-does-it-work?utm_source=chatgpt.com "FPL 2025-26: What is Fantasy Premier League and how does it work?"
