# Fantasy Premier League Squad Optimization

This project implements the `select_initial_squad` function according to the formal specification in `formal_spec.md`. It optimally selects a 15-player FPL squad for gameweeks 1-4 that maximizes expected points while respecting all constraints.

## Features

✅ **Complete Implementation**: Fully implements the formal specification  
✅ **Mixed Integer Programming**: Uses PuLP for optimal solutions  
✅ **Genetic Algorithm Fallback**: Alternative solver implementation  
✅ **Constraint Handling**: Budget, position quotas, and club limits  
✅ **Fixture Integration**: Incorporates fixture difficulty into optimization  
✅ **Error Handling**: Proper validation and custom exceptions  
✅ **Unit Tests**: Comprehensive test suite covering all specification requirements  
✅ **Real Data Integration**: Works with live FPL API data and fixtures  

## Installation

```bash
pip install pandas numpy pulp ortools requests
```

## Usage

### Basic Usage

```python
from main import select_initial_squad, load_fpl_data

# Load real FPL data
players_df, fixtures_df, _ = load_fpl_data()

# Select optimal squad
result = select_initial_squad(players_df, fixtures_df)

print(f"Total cost: £{result.total_cost:.1f}m")
print(f"Expected points: {result.expected_points:.1f}")
print(f"Squad: {len(result.squad_df)} players")
```

### Advanced Usage

```python
# Custom parameters
result = select_initial_squad(
    players_df, 
    fixtures_df,
    gw_start=1,
    gw_end=6,  # Optimize for GW1-6 instead
    budget_million=95.0,  # Leave £5m in bank
    solver="ga"  # Use genetic algorithm
)

# Access detailed results
print("Position breakdown:", result.per_position)
print("Club distribution:", result.club_counts)
print("Selected players:")
print(result.squad_df[['first_name', 'second_name', 'position', 'now_cost']])
```

## Key Classes

### SquadResult

The optimization result containing:
- `squad_df`: DataFrame with 15 selected players
- `total_cost`: Total squad cost in millions
- `expected_points`: Sum of expected points (fixture-adjusted)
- `per_position`: Players by position
- `club_counts`: Players per club
- `objective_details`: Solver diagnostics
- `fixtures_info`: Fixture difficulty and upcoming matches

### Custom Exceptions

- `InfeasibleError`: Raised when no valid squad can be constructed within constraints

## Constraint Handling

The optimizer respects all official FPL rules:

1. **Squad Size**: Exactly 15 players
2. **Position Quotas**: 2 GK, 5 DEF, 5 MID, 3 FWD
3. **Budget**: Total cost ≤ £100m (configurable)
4. **Club Limit**: Max 3 players per Premier League club

## Solvers

### MIP Solver (Default)
- Uses Mixed Integer Linear Programming via PuLP
- Guarantees optimal solution
- Fast for typical problem sizes

### GA Solver (Fallback)
- Genetic Algorithm implementation
- Good for when MIP fails or for experimentation
- Heuristic-based (may not find global optimum)

## Testing

Run the test suite:

```bash
python test_squad_selection.py  # Unit tests
python test_integration.py      # Integration test with real data
```

## Performance

- Handles full FPL player database (600+ players)
- Typical solve time: < 5 seconds on modern hardware
- Memory efficient implementation

## Files

- `main.py`: Core implementation
- `formal_spec.md`: Detailed specification
- `test_squad_selection.py`: Unit tests
- `test_integration.py`: Real data integration test
- `fpl_data.json`: Cached FPL API data

## Fixture Difficulty Integration

The optimizer incorporates fixture difficulty ratings to adjust expected points:

### Difficulty Multipliers

- **Difficulty 1 (easiest)** → ×1.4 (40% points boost)
- **Difficulty 2** → ×1.2 (20% points boost)  
- **Difficulty 3** → ×1.0 (neutral)
- **Difficulty 4** → ×0.8 (20% points penalty)
- **Difficulty 5 (hardest)** → ×0.6 (40% points penalty)

### Impact on Selection

Players from teams with easier fixtures get higher expected points, making them more likely to be selected. This creates a realistic balance between player quality and fixture difficulty.

**Example**: A £6m midfielder facing difficulty 2 opponents becomes more valuable than a similar midfielder facing difficulty 4 opponents, even if their base stats are identical.

### How It Works

1. **Base Expected Points**: Calculated from last season's total points / 38 gameweeks
2. **Fixture Multiplier**: Applied per gameweek based on opponent difficulty
3. **Final Expected Points**: Base points × Fixture multiplier for each GW
4. **Optimization**: Algorithm maximizes sum of fixture-adjusted expected points

### Calculation Formula

```
Fixture Multiplier = 1.6 - (Difficulty × 0.2)
Expected Points GW = Base Points × Fixture Multiplier
```

This means teams with consistently easy fixtures (difficulty 1-2) will have more players selected, while teams with tough fixtures (difficulty 4-5) will be underrepresented.

## API Data Sources

Live data is fetched from the official FPL API:
```
Player Data: https://fantasy.premierleague.com/api/bootstrap-static/
Fixtures: https://fantasy.premierleague.com/api/fixtures/
```

The optimizer incorporates fixture difficulty ratings (1=easiest, 5=hardest) to adjust expected points based on opponent strength.

## Future Enhancements

The specification includes extensibility hooks for:
- Custom constraints
- Alternative objective functions  
- Custom solvers
- Captain/vice-captain selection (out of scope for V1)

---

*This implementation follows the formal specification exactly and has been tested with real FPL data to ensure correctness and reliability.*
