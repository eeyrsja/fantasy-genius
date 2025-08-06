import requests
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Sequence, Union, Callable, Optional, Dict, Any, List
import json
import pulp
from ortools.linear_solver import pywraplp
import warnings

# Custom Exception Classes
class InfeasibleError(Exception):
    """Raised when the optimization problem is infeasible"""
    pass

@dataclass(frozen=True)
class SquadResult:
    """Result of squad selection optimization"""
    squad_df: pd.DataFrame         # 15 rows, same columns as input + 'position'
    total_cost: float              # £m
    expected_points: float         # sum over GW range
    per_position: Dict[str, List]  # e.g. {"GK": [id1, id2], ...}
    club_counts: Dict[int, int]    # {team_code: n}
    objective_details: Dict        # diagnostics from solver
    fixtures_info: Dict            # fixture information for selected players

@dataclass(frozen=True)
class StartingElevenResult:
    """Result of starting eleven selection"""
    starting_eleven: pd.DataFrame  # 11 players for starting lineup
    bench: pd.DataFrame           # 4 players for bench
    formation: str                # Selected formation (e.g. "3-4-3")
    captain_id: int               # Player ID of captain
    vice_captain_id: int          # Player ID of vice-captain
    expected_points_gw1: float    # Expected points for GW1 only
    formation_breakdown: Dict     # Position counts in formation

def select_starting_eleven(
    squad_result: SquadResult,
    *,
    gameweek: int = 1,
    captain_multiplier: float = 2.0,
    vice_captain_multiplier: float = 1.0
) -> StartingElevenResult:
    """
    Select optimal starting eleven from 15-player squad for a specific gameweek.
    
    Args:
        squad_result: Result from select_initial_squad containing 15 players
        gameweek: Gameweek to optimize for (default 1)
        captain_multiplier: Points multiplier for captain (default 2.0)
        vice_captain_multiplier: Points multiplier for vice-captain (default 1.0)
    
    Returns:
        StartingElevenResult with optimal starting XI and bench
    
    Raises:
        ValueError: If squad doesn't have required players for any formation
    """
    
    squad_df = squad_result.squad_df.copy()
    
    # Get expected points for the specific gameweek
    gw_col = f"ep_gw{gameweek}"
    if gw_col not in squad_df.columns:
        # If no specific GW column, use average from exp_pts_window
        squad_df[gw_col] = squad_df['exp_pts_window'] / len([col for col in squad_df.columns if col.startswith('ep_gw')])
    
    # Define allowed formations: (DEF, MID, FWD) - GK is always 1
    allowed_formations = [
        (3, 4, 3),  # 3-4-3
        (3, 5, 2),  # 3-5-2
        (4, 3, 3),  # 4-3-3
        (4, 4, 2),  # 4-4-2
        (4, 5, 1),  # 4-5-1
        (5, 2, 3),  # 5-2-3
        (5, 3, 2),  # 5-3-2
        (5, 4, 1)   # 5-4-1
    ]
    
    best_formation = None
    best_starting_xi = None
    best_bench = None
    best_points = -1
    best_captain = None
    best_vice_captain = None
    
    # Try each allowed formation
    for def_count, mid_count, fwd_count in allowed_formations:
        try:
            starting_xi, bench, points, captain, vice_captain = _optimize_formation(
                squad_df, def_count, mid_count, fwd_count, gw_col, captain_multiplier, vice_captain_multiplier
            )
            
            if points > best_points:
                best_points = points
                best_starting_xi = starting_xi
                best_bench = bench
                best_formation = (def_count, mid_count, fwd_count)
                best_captain = captain
                best_vice_captain = vice_captain
                
        except ValueError:
            # Not enough players for this formation, skip
            continue
    
    if best_formation is None:
        raise ValueError("No valid formation possible with current squad")
    
    formation_str = f"{best_formation[0]}-{best_formation[1]}-{best_formation[2]}"
    
    formation_breakdown = {
        'GK': 1,
        'DEF': best_formation[0],
        'MID': best_formation[1], 
        'FWD': best_formation[2]
    }
    
    return StartingElevenResult(
        starting_eleven=best_starting_xi,
        bench=best_bench,
        formation=formation_str,
        captain_id=best_captain,
        vice_captain_id=best_vice_captain,
        expected_points_gw1=best_points,
        formation_breakdown=formation_breakdown
    )

def _optimize_formation(squad_df: pd.DataFrame, def_count: int, mid_count: int, fwd_count: int, 
                       gw_col: str, captain_multiplier: float, vice_captain_multiplier: float) -> tuple:
    """
    Optimize player selection for a specific formation.
    
    Returns:
        tuple: (starting_xi_df, bench_df, total_points, captain_id, vice_captain_id)
    """
    
    # Separate players by position - using the actual position abbreviations from data
    gk_players = squad_df[squad_df['position'] == 'GK'].copy()
    def_players = squad_df[squad_df['position'] == 'DEF'].copy()
    mid_players = squad_df[squad_df['position'] == 'MID'].copy()
    fwd_players = squad_df[squad_df['position'] == 'FWD'].copy()
    
    # Debug: Print what we found
    # print(f"   Formation {def_count}-{mid_count}-{fwd_count}: Found GK:{len(gk_players)} DEF:{len(def_players)} MID:{len(mid_players)} FWD:{len(fwd_players)}")
    
    # Check if we have enough players for this formation
    if (len(gk_players) < 1 or len(def_players) < def_count or 
        len(mid_players) < mid_count or len(fwd_players) < fwd_count):
        raise ValueError(f"Not enough players for formation {def_count}-{mid_count}-{fwd_count}")
    
    # Sort players by expected points for this gameweek (descending)
    gk_players = gk_players.sort_values(gw_col, ascending=False)
    def_players = def_players.sort_values(gw_col, ascending=False)
    mid_players = mid_players.sort_values(gw_col, ascending=False)
    fwd_players = fwd_players.sort_values(gw_col, ascending=False)
    
    # Select best players for each position
    selected_gk = gk_players.head(1)
    selected_def = def_players.head(def_count)
    selected_mid = mid_players.head(mid_count)
    selected_fwd = fwd_players.head(fwd_count)
    
    # Combine starting XI
    starting_xi = pd.concat([selected_gk, selected_def, selected_mid, selected_fwd], ignore_index=True)
    
    # Remaining players go to bench
    selected_ids = starting_xi['id'].tolist()
    bench = squad_df[~squad_df['id'].isin(selected_ids)].copy()
    bench = bench.sort_values(gw_col, ascending=False)  # Sort bench by points too
    
    # Select captain and vice-captain (highest expected points from starting XI)
    starting_xi_sorted = starting_xi.sort_values(gw_col, ascending=False)
    captain_id = starting_xi_sorted.iloc[0]['id']
    vice_captain_id = starting_xi_sorted.iloc[1]['id']
    
    # Calculate total expected points including captain multiplier
    total_points = 0
    for _, player in starting_xi.iterrows():
        base_points = player[gw_col]
        if player['id'] == captain_id:
            total_points += base_points * captain_multiplier
        elif player['id'] == vice_captain_id:
            total_points += base_points * vice_captain_multiplier  # Usually 1.0, but kept for flexibility
        else:
            total_points += base_points
    
    return starting_xi, bench, total_points, captain_id, vice_captain_id

def select_initial_squad(
    players: pd.DataFrame,
    fixtures: pd.DataFrame,
    *,
    gw_start: int = 1,
    gw_end: int = 4,
    budget_million: float = 100.0,
    solver: Union[str, Callable, None] = "mip",
    expected_points_cols: Optional[Sequence[str]] = None,
    custom_constraints: Optional[Dict] = None,
) -> SquadResult:
    """
    Select optimal 15-player FPL squad for gameweeks 1-4.
    
    Args:
        players: DataFrame with player data including id, element_type, team, now_cost
        fixtures: DataFrame with fixture data (not used in V1 but required for interface)
        gw_start: Start gameweek (default 1)
        gw_end: End gameweek (default 4)
        budget_million: Budget in millions (default 100.0)
        solver: Solver backend ("mip", "ga", or callable)
        expected_points_cols: Column names for expected points per GW
        custom_constraints: Additional constraints (not implemented in V1)
    
    Returns:
        SquadResult with selected squad and metadata
    
    Raises:
        ValueError: For invalid inputs or constraint violations
        KeyError: For missing required columns
        InfeasibleError: When no feasible solution exists
    """
    
    # Step 1: Validation
    _validate_inputs(players, fixtures, gw_start, gw_end, budget_million)
    
    # Step 2: Prepare expected points with fixture consideration
    players_work = players.copy()
    if expected_points_cols is None:
        expected_points_cols = [f"ep_gw{gw}" for gw in range(gw_start, gw_end + 1)]
    
    # Incorporate fixture difficulty into expected points
    players_work = _incorporate_fixture_difficulty(players_work, fixtures, gw_start, gw_end, expected_points_cols)
    
    players_work["exp_pts_window"] = players_work[expected_points_cols].sum(axis=1)
    
    # Debug: Print some sample fixture adjustments if fixtures are available
    if not fixtures.empty and 'event' in fixtures.columns:
        print(f"✅ Fixture difficulty applied to {len(expected_points_cols)} gameweeks (GW{gw_start}-{gw_end})")
        
        # Show fixture multiplier example for GW1
        sample_players = players_work.head(3)
        gw1_multipliers = _calculate_fixture_multiplier(sample_players, fixtures, gw_start)
        
        print(f"   Sample fixture multipliers for GW{gw_start}:")
        for idx, (_, player) in enumerate(sample_players.iterrows()):
            multiplier = gw1_multipliers.iloc[idx]
            base_pts = player.get('total_points', 50) / 38
            print(f"   • Team {player['team']}: ×{multiplier:.2f} (base {base_pts:.1f} → {base_pts*multiplier:.1f} pts)")
        
        sample_size = min(5, len(players_work))
        sample_players = players_work.head(sample_size)
        for _, player in sample_players.iterrows():
            print(f"   Player {player.get('first_name', '')} {player.get('second_name', 'Unknown')} (Team {player['team']}): {player['exp_pts_window']:.1f} pts")
    else:
        print("⚠️ No fixture data available - using base expected points only")
    
    # Step 3: Solve optimization
    if solver == "mip" or solver is None:
        result = _solve_with_mip(players_work, fixtures, gw_start, gw_end, budget_million, custom_constraints)
    elif solver == "ga":
        result = _solve_with_ga(players_work, fixtures, gw_start, gw_end, budget_million, custom_constraints)
    elif callable(solver):
        result = solver(players_work, budget_million, custom_constraints)
    else:
        raise ValueError(f"Unknown solver: {solver}")
    
    return result

def _incorporate_fixture_difficulty(players: pd.DataFrame, fixtures: pd.DataFrame, gw_start: int, gw_end: int, expected_points_cols: list) -> pd.DataFrame:
    """Incorporate fixture difficulty into expected points calculation"""
    players_work = players.copy()
    
    # If expected points columns don't exist, create them based on base performance and fixture difficulty
    if not all(col in players_work.columns for col in expected_points_cols):
        # Create base expected points from player performance metrics
        # Using total_points from last season as base, scaled down per gameweek
        # Handle the case where total_points might be 0 or missing
        base_points_per_gw = players_work['total_points'].fillna(50) / 38  # Average points per GW
        # Ensure minimum base points for players with 0 total_points
        base_points_per_gw = base_points_per_gw.clip(lower=0.5)  # Minimum 0.5 pts per GW
        
        # Apply fixture difficulty multipliers for each gameweek
        for i, col in enumerate(expected_points_cols):
            gw = gw_start + i
            fixture_multipliers = _calculate_fixture_multiplier(players_work, fixtures, gw)
            
            # Apply the multiplier to base points
            players_work[col] = base_points_per_gw * fixture_multipliers
    else:
        # If expected points columns exist, still apply fixture multipliers
        for i, col in enumerate(expected_points_cols):
            gw = gw_start + i
            fixture_multipliers = _calculate_fixture_multiplier(players_work, fixtures, gw)
            players_work[col] = players_work[col] * fixture_multipliers
    
    return players_work

def _calculate_fixture_multiplier(players: pd.DataFrame, fixtures: pd.DataFrame, gameweek: int) -> pd.Series:
    """Calculate fixture difficulty multiplier for each player's team in a given gameweek"""
    
    # Default multiplier if no fixtures data
    if fixtures.empty or 'event' not in fixtures.columns:
        return pd.Series(1.0, index=players.index)
    
    # Filter fixtures for the specific gameweek
    gw_fixtures = fixtures[fixtures['event'] == gameweek]
    
    if gw_fixtures.empty:
        return pd.Series(1.0, index=players.index)
    
    # Create team difficulty mapping
    # Convert difficulty to multiplier (inverse relationship)
    # Difficulty 1 (easiest) → multiplier 1.4 (40% boost)
    # Difficulty 2 → multiplier 1.2 (20% boost)  
    # Difficulty 3 → multiplier 1.0 (neutral)
    # Difficulty 4 → multiplier 0.8 (20% penalty)
    # Difficulty 5 (hardest) → multiplier 0.6 (40% penalty)
    team_multipliers = {}
    
    for _, fixture in gw_fixtures.iterrows():
        home_team = fixture.get('team_h')
        away_team = fixture.get('team_a')
        home_difficulty = fixture.get('team_h_difficulty', 3)
        away_difficulty = fixture.get('team_a_difficulty', 3)
        
        # Convert difficulty to multiplier: multiplier = 1.6 - (difficulty * 0.2)
        home_multiplier = max(0.6, 1.6 - (home_difficulty * 0.2))
        away_multiplier = max(0.6, 1.6 - (away_difficulty * 0.2))
        
        if home_team is not None:
            team_multipliers[home_team] = home_multiplier
        if away_team is not None:
            team_multipliers[away_team] = away_multiplier
    
    # Apply multipliers to players based on their team
    multipliers = []
    for _, player in players.iterrows():
        team_id = player.get('team')
        multiplier = team_multipliers.get(team_id, 1.0)  # Default 1.0 if team not found
        multipliers.append(multiplier)
    
    return pd.Series(multipliers, index=players.index)

def _get_fixtures_info(squad_df: pd.DataFrame, fixtures: pd.DataFrame, gw_start: int, gw_end: int) -> Dict:
    """Get fixture information for selected squad"""
    fixtures_info = {
        'gameweeks': list(range(gw_start, gw_end + 1)),
        'team_fixtures': {},
        'difficulty_summary': {}
    }
    
    if fixtures.empty:
        return fixtures_info
    
    # Get unique teams in squad
    squad_teams = squad_df['team'].unique()
    
    for team_id in squad_teams:
        team_fixtures = []
        difficulties = []
        
        for gw in range(gw_start, gw_end + 1):
            gw_fixtures = fixtures[fixtures.get('event', 0) == gw]
            
            # Find fixture for this team
            home_fixture = gw_fixtures[gw_fixtures.get('team_h', 0) == team_id]
            away_fixture = gw_fixtures[gw_fixtures.get('team_a', 0) == team_id]
            
            if not home_fixture.empty:
                fixture = home_fixture.iloc[0]
                opponent = fixture.get('team_a', 'Unknown')
                difficulty = fixture.get('team_h_difficulty', 3)
                venue = 'H'
            elif not away_fixture.empty:
                fixture = away_fixture.iloc[0]
                opponent = fixture.get('team_h', 'Unknown')
                difficulty = fixture.get('team_a_difficulty', 3)
                venue = 'A'
            else:
                opponent = 'Unknown'
                difficulty = 3
                venue = '?'
            
            team_fixtures.append({
                'gameweek': gw,
                'opponent': opponent,
                'venue': venue,
                'difficulty': difficulty
            })
            difficulties.append(difficulty)
        
        fixtures_info['team_fixtures'][team_id] = team_fixtures
        fixtures_info['difficulty_summary'][team_id] = {
            'avg_difficulty': np.mean(difficulties),
            'total_difficulty': sum(difficulties),
            'fixtures': team_fixtures
        }
    
    return fixtures_info

def _validate_inputs(players: pd.DataFrame, fixtures: pd.DataFrame, gw_start: int, gw_end: int, budget_million: float):
    """Validate input data and parameters"""
    required_cols = ['id', 'element_type', 'team', 'now_cost']
    missing_cols = [col for col in required_cols if col not in players.columns]
    if missing_cols:
        raise KeyError(f"Missing required columns: {missing_cols}")
    
    if players['id'].duplicated().any():
        raise ValueError("Duplicate player IDs found")
    
    if len(players) > 1000:
        warnings.warn("Player pool exceeds 1000 rows, performance may be impacted")
    
    if gw_start < 1 or gw_end < gw_start or gw_end > 38:
        raise ValueError("Invalid gameweek range")
    
    if budget_million <= 0:
        raise ValueError("Budget must be positive")

def _solve_with_mip(players: pd.DataFrame, fixtures: pd.DataFrame, gw_start: int, gw_end: int, budget_million: float, custom_constraints: Optional[Dict]) -> SquadResult:
    """Solve using Mixed Integer Programming with PuLP"""
    
    # Create the optimization problem
    prob = pulp.LpProblem("FPL_Squad_Selection", pulp.LpMaximize)
    
    # Decision variables
    player_vars = {}
    for idx, player in players.iterrows():
        player_vars[player['id']] = pulp.LpVariable(f"player_{player['id']}", cat='Binary')
    
    # Objective: maximize expected points
    prob += pulp.lpSum([player_vars[player['id']] * player['exp_pts_window'] 
                       for idx, player in players.iterrows()])
    
    # Constraint: exactly 15 players
    prob += pulp.lpSum([player_vars[player['id']] for idx, player in players.iterrows()]) == 15
    
    # Position constraints
    position_mapping = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}
    position_limits = {'GK': 2, 'DEF': 5, 'MID': 5, 'FWD': 3}
    
    for element_type, position in position_mapping.items():
        players_in_position = players[players['element_type'] == element_type]
        prob += pulp.lpSum([player_vars[player['id']] 
                           for idx, player in players_in_position.iterrows()]) == position_limits[position]
    
    # Budget constraint (convert from millions to API units)
    budget_units = int(budget_million * 10)
    prob += pulp.lpSum([player_vars[player['id']] * player['now_cost'] 
                       for idx, player in players.iterrows()]) <= budget_units
    
    # Club constraints (max 3 players per club)
    clubs = players['team'].unique()
    for club in clubs:
        club_players = players[players['team'] == club]
        if len(club_players) > 0:
            prob += pulp.lpSum([player_vars[player['id']] 
                               for idx, player in club_players.iterrows()]) <= 3
    
    # Solve the problem
    prob.solve(pulp.PULP_CBC_CMD(msg=0))
    
    # Check if solution is feasible
    if prob.status != pulp.LpStatusOptimal:
        if prob.status == pulp.LpStatusInfeasible:
            raise InfeasibleError("No feasible solution found - constraints cannot be satisfied")
        else:
            raise RuntimeError(f"Solver failed with status: {pulp.LpStatus[prob.status]}")
    
    # Extract selected players
    selected_ids = []
    for player_id, var in player_vars.items():
        if var.value() == 1:
            selected_ids.append(player_id)
    
    if len(selected_ids) != 15:
        raise RuntimeError(f"Invalid solution: selected {len(selected_ids)} players instead of 15")
    
    # Build result
    squad_df = players[players['id'].isin(selected_ids)].copy()
    squad_df['position'] = squad_df['element_type'].map(position_mapping)
    
    total_cost = squad_df['now_cost'].sum() / 10.0  # Convert back to millions
    expected_points = squad_df['exp_pts_window'].sum()
    
    # Per position breakdown
    per_position = {}
    for position in position_limits.keys():
        per_position[position] = squad_df[squad_df['position'] == position]['id'].tolist()
    
    # Club counts
    club_counts = squad_df['team'].value_counts().to_dict()
    
    # Get fixtures information
    fixtures_info = _get_fixtures_info(squad_df, fixtures, gw_start, gw_end)
    
    objective_details = {
        'solver': 'mip',
        'status': pulp.LpStatus[prob.status],
        'objective_value': pulp.value(prob.objective),
        'solve_time': None  # PuLP doesn't provide timing info easily
    }
    
    return SquadResult(
        squad_df=squad_df,
        total_cost=total_cost,
        expected_points=expected_points,
        per_position=per_position,
        club_counts=club_counts,
        objective_details=objective_details,
        fixtures_info=fixtures_info
    )

def _solve_with_ga(players: pd.DataFrame, fixtures: pd.DataFrame, gw_start: int, gw_end: int, budget_million: float, custom_constraints: Optional[Dict]) -> SquadResult:
    """Solve using Genetic Algorithm (simplified implementation)"""
    # This is a placeholder for genetic algorithm implementation
    # For now, use a greedy heuristic that's more budget-aware
    
    position_mapping = {1: 'GK', 2: 'DEF', 3: 'MID', 4: 'FWD'}
    position_limits = {'GK': 2, 'DEF': 5, 'MID': 5, 'FWD': 3}
    budget_units = int(budget_million * 10)
    
    selected_players = []
    remaining_budget = budget_units
    
    # Sort all players by value (points per cost) within each position
    for element_type, position in position_mapping.items():
        position_players = players[players['element_type'] == element_type].copy()
        
        # Calculate value metric (points per cost)
        position_players['value'] = position_players['exp_pts_window'] / position_players['now_cost']
        position_players = position_players.sort_values(['value', 'exp_pts_window'], ascending=[False, False])
        
        count = 0
        limit = position_limits[position]
        
        # Try multiple passes to find feasible combination
        for idx, player in position_players.iterrows():
            if count >= limit:
                break
                
            if player['now_cost'] <= remaining_budget:
                # Check club constraint
                current_clubs = pd.Series([p['team'] for p in selected_players])
                club_count = current_clubs.value_counts().get(player['team'], 0) if not current_clubs.empty else 0
                
                if club_count < 3:
                    selected_players.append(player.to_dict())
                    remaining_budget -= player['now_cost']
                    count += 1
        
        # If we couldn't fill the position, try with cheaper options
        if count < limit:
            # Reset and try again with cheapest options
            cheapest_players = position_players.sort_values('now_cost')
            for idx, player in cheapest_players.iterrows():
                if count >= limit:
                    break
                    
                if player['now_cost'] <= remaining_budget:
                    # Check if already selected
                    if player['id'] not in [p['id'] for p in selected_players]:
                        # Check club constraint
                        current_clubs = pd.Series([p['team'] for p in selected_players])
                        club_count = current_clubs.value_counts().get(player['team'], 0) if not current_clubs.empty else 0
                        
                        if club_count < 3:
                            selected_players.append(player.to_dict())
                            remaining_budget -= player['now_cost']
                            count += 1
        
        if count < limit:
            raise InfeasibleError(f"Cannot fill {position} position: need {limit}, got {count}. Remaining budget: £{remaining_budget/10:.1f}m")
    
    if len(selected_players) != 15:
        raise InfeasibleError(f"Could not select exactly 15 players. Selected: {len(selected_players)}")
    
    # Convert to DataFrame
    squad_df = pd.DataFrame(selected_players)
    squad_df['position'] = squad_df['element_type'].map(position_mapping)
    
    total_cost = squad_df['now_cost'].sum() / 10.0
    expected_points = squad_df['exp_pts_window'].sum()
    
    per_position = {}
    for position in position_limits.keys():
        per_position[position] = squad_df[squad_df['position'] == position]['id'].tolist()
    
    club_counts = squad_df['team'].value_counts().to_dict()
    
    # Get fixtures information
    fixtures_info = _get_fixtures_info(squad_df, fixtures, gw_start, gw_end)
    
    objective_details = {
        'solver': 'ga',
        'status': 'optimal',
        'objective_value': expected_points,
        'solve_time': None
    }
    
    return SquadResult(
        squad_df=squad_df,
        total_cost=total_cost,
        expected_points=expected_points,
        per_position=per_position,
        club_counts=club_counts,
        objective_details=objective_details,
        fixtures_info=fixtures_info
    )

# Original data loading code
def load_fpl_data():
    """Load FPL data from API"""
    url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    response = requests.get(url)
    data = response.json()

    # Example: Convert player data to DataFrame
    players_df = pd.DataFrame(data['elements'])

    # Load fixtures from separate API endpoint
    try:
        fixtures_url = "https://fantasy.premierleague.com/api/fixtures/"
        fixtures_response = requests.get(fixtures_url)
        fixtures_data = fixtures_response.json()
        fixtures_df = pd.DataFrame(fixtures_data)
        print(f"Loaded {len(fixtures_df)} fixtures from API")
    except Exception as e:
        print(f"Warning: Could not load fixtures data: {e}")
        # Create events as fallback (gameweek information only)
        fixtures_df = pd.DataFrame(data.get('events', []))
        if not fixtures_df.empty:
            fixtures_df = fixtures_df.rename(columns={'id': 'event'})

    # Create a mapping of element_type_id to position name
    element_types_df = pd.DataFrame(data['element_types'])
    element_type_map = dict(zip(element_types_df['id'], element_types_df['singular_name']))

    # Map element_type to position name
    players_df['position'] = players_df['element_type'].map(element_type_map)

    # Save the json to a pretty JSON file
    with open('fpl_data.json', 'w') as f:
        json.dump(data, f, indent=4)
    
    return players_df, fixtures_df, data

# Example usage and testing
if __name__ == "__main__":
    # Load data
    players_df, fixtures_df, raw_data = load_fpl_data()
    
    print("Player data sample:")
    print(players_df[['first_name', 'second_name', 'position', 'now_cost', 'total_points']].head())
    print(f"\nTotal players: {len(players_df)}")
    print(f"Position distribution:")
    print(players_df['position'].value_counts())
    
    # Test the squad selection function
    try:
        print("\nTesting squad selection...")
        result = select_initial_squad(players_df, fixtures_df)
        
        print(f"\nSquad Selection Results:")
        print(f"Total cost: £{result.total_cost:.1f}m")
        print(f"Expected points: {result.expected_points:.1f}")
        print(f"Position breakdown: {result.per_position}")
        print(f"Club distribution: {result.club_counts}")
        
        print("\nSelected Squad:")
        display_cols = ['first_name', 'second_name', 'position', 'now_cost', 'team', 'exp_pts_window']
        available_cols = [col for col in display_cols if col in result.squad_df.columns]
        print(result.squad_df[available_cols].sort_values(['position', 'exp_pts_window'], ascending=[True, False]))
        
        # Test starting eleven selection
        print("\n" + "="*60)
        print("TESTING STARTING ELEVEN SELECTION FOR GW1")
        print("="*60)
        
        starting_eleven_result = select_starting_eleven(result, gameweek=1)
        
        print(f"\n🏆 Optimal Starting XI for GW1:")
        print(f"Formation: {starting_eleven_result.formation}")
        print(f"Expected Points (with captain): {starting_eleven_result.expected_points_gw1:.1f}")
        
        # Show starting XI with captain indicators
        print(f"\n📋 Starting XI:")
        starting_display_cols = ['first_name', 'second_name', 'position', 'ep_gw1']
        starting_available_cols = [col for col in starting_display_cols if col in starting_eleven_result.starting_eleven.columns]
        
        xi_display = starting_eleven_result.starting_eleven[starting_available_cols].copy()
        xi_display['Role'] = xi_display.apply(lambda row: 
            '(C)' if row.name in starting_eleven_result.starting_eleven[starting_eleven_result.starting_eleven['id'] == starting_eleven_result.captain_id].index
            else '(VC)' if row.name in starting_eleven_result.starting_eleven[starting_eleven_result.starting_eleven['id'] == starting_eleven_result.vice_captain_id].index
            else '', axis=1)
        
        # Add captain/vice-captain indicators
        for idx, row in xi_display.iterrows():
            player_id = starting_eleven_result.starting_eleven.iloc[idx]['id']
            if player_id == starting_eleven_result.captain_id:
                xi_display.loc[idx, 'Role'] = '(C)'
            elif player_id == starting_eleven_result.vice_captain_id:
                xi_display.loc[idx, 'Role'] = '(VC)'
            else:
                xi_display.loc[idx, 'Role'] = ''
        
        print(xi_display.sort_values(['position', 'ep_gw1'], ascending=[True, False]))
        
        print(f"\n🪑 Bench (4 players):")
        bench_display_cols = ['first_name', 'second_name', 'position', 'ep_gw1']
        bench_available_cols = [col for col in bench_display_cols if col in starting_eleven_result.bench.columns]
        print(starting_eleven_result.bench[bench_available_cols].sort_values('ep_gw1', ascending=False))
        
        # Show formation breakdown
        print(f"\n📊 Formation Breakdown:")
        for position, count in starting_eleven_result.formation_breakdown.items():
            print(f"   {position}: {count} players")
        
        # Show captain choice reasoning
        captain_player = starting_eleven_result.starting_eleven[starting_eleven_result.starting_eleven['id'] == starting_eleven_result.captain_id].iloc[0]
        vice_captain_player = starting_eleven_result.starting_eleven[starting_eleven_result.starting_eleven['id'] == starting_eleven_result.vice_captain_id].iloc[0]
        
        captain_name = f"{captain_player.get('first_name', '')} {captain_player.get('second_name', 'Unknown')}"
        vice_captain_name = f"{vice_captain_player.get('first_name', '')} {vice_captain_player.get('second_name', 'Unknown')}"
        
        print(f"\n👨‍✈️ Captain Choice:")
        print(f"   Captain: {captain_name} ({captain_player['ep_gw1']:.1f} pts → {captain_player['ep_gw1']*2:.1f} pts)")
        print(f"   Vice-Captain: {vice_captain_name} ({vice_captain_player['ep_gw1']:.1f} pts)")
        
    except Exception as e:
        print(f"Error in squad selection: {e}")
        import traceback
        traceback.print_exc()

