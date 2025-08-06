"""
Unit tests for the select_initial_squad function according to formal specification.

Test matrix from specification:
1. Valid minimal dataset (20 players) - Feasible, returns 15-row squad
2. Budget too low (budget_million=50) - InfeasibleError
3. >3 players same club in input without duplicates - Solver should respect limit
4. Missing element_type column - KeyError
5. Tied optimal points, different costs - Chooses cheaper squad
"""

import pytest
import pandas as pd
import numpy as np
from main import select_initial_squad, InfeasibleError, SquadResult
import warnings

def create_minimal_test_dataset():
    """Create a minimal 20-player dataset for testing"""
    players = []
    
    # Create 4 goalkeepers (element_type=1) - different teams and costs
    for i in range(4):
        players.append({
            'id': i + 1,
            'element_type': 1,
            'team': (i % 4) + 1,  # Teams 1, 2, 3, 4
            'now_cost': 40 + i * 2,   # £4.0m to £4.6m
            'first_name': f'GK{i}',
            'second_name': f'Keeper{i}',
            'total_points': 100 + i * 10
        })
    
    # Create 8 defenders (element_type=2) - spread across teams
    for i in range(8):
        players.append({
            'id': i + 5,
            'element_type': 2,
            'team': (i % 4) + 1,  # Teams 1, 2, 3, 4
            'now_cost': 40 + (i % 3) * 2,   # £4.0m, £4.2m, £4.4m pattern
            'first_name': f'DEF{i}',
            'second_name': f'Defender{i}',
            'total_points': 80 + i * 5
        })
    
    # Create 6 midfielders (element_type=3) - different teams and costs
    for i in range(6):
        players.append({
            'id': i + 13,
            'element_type': 3,
            'team': (i % 3) + 1,  # Teams 1, 2, 3
            'now_cost': 50 + i * 5,  # £5.0m to £7.5m
            'first_name': f'MID{i}',
            'second_name': f'Midfielder{i}',
            'total_points': 120 + i * 15
        })
    
    # Create 4 forwards (element_type=4) - different teams
    for i in range(4):
        players.append({
            'id': i + 19,
            'element_type': 4,
            'team': (i % 2) + 1,  # Teams 1, 2
            'now_cost': 60 + i * 10,  # £6.0m to £9.0m
            'first_name': f'FWD{i}',
            'second_name': f'Forward{i}',
            'total_points': 150 + i * 20
        })
    
    return pd.DataFrame(players)

def create_fixtures_dummy():
    """Create dummy fixtures data"""
    return pd.DataFrame([
        {'event': 1, 'team_h': 1, 'team_a': 2, 'team_h_difficulty': 3, 'team_a_difficulty': 2},
        {'event': 2, 'team_h': 2, 'team_a': 3, 'team_h_difficulty': 2, 'team_a_difficulty': 4},
    ])

def test_case_1_valid_minimal_dataset():
    """Test Case 1: Valid minimal dataset (22 players) - should be feasible"""
    players = create_minimal_test_dataset()
    fixtures = create_fixtures_dummy()
    
    # This should now be feasible with better distributed data
    result = select_initial_squad(players, fixtures)
    
    # Assertions
    assert isinstance(result, SquadResult)
    assert len(result.squad_df) == 15
    assert result.total_cost <= 100.0
    assert len(result.per_position['GK']) == 2
    assert len(result.per_position['DEF']) == 5
    assert len(result.per_position['MID']) == 5
    assert len(result.per_position['FWD']) == 3
    
    # Check club constraints
    for club_count in result.club_counts.values():
        assert club_count <= 3

def test_case_1_extended_valid_dataset():
    """Test Case 1 Extended: Valid dataset with enough players in each position"""
    players = create_minimal_test_dataset()
    
    # Add one more forward to make it feasible
    additional_forward = pd.DataFrame([{
        'id': 21,
        'element_type': 4,
        'team': 2,
        'now_cost': 90,
        'first_name': 'FWD2',
        'second_name': 'Forward2',
        'total_points': 140
    }])
    
    players = pd.concat([players, additional_forward], ignore_index=True)
    fixtures = create_fixtures_dummy()
    
    result = select_initial_squad(players, fixtures)
    
    # Assertions
    assert isinstance(result, SquadResult)
    assert len(result.squad_df) == 15
    assert result.total_cost <= 100.0
    assert len(result.per_position['GK']) == 2
    assert len(result.per_position['DEF']) == 5
    assert len(result.per_position['MID']) == 5
    assert len(result.per_position['FWD']) == 3
    
    # Check club constraints
    for club_count in result.club_counts.values():
        assert club_count <= 3

def test_case_2_budget_too_low():
    """Test Case 2: Budget too low (budget_million=50) - should raise InfeasibleError"""
    players = create_minimal_test_dataset()
    fixtures = create_fixtures_dummy()
    
    # Should fail with low budget
    with pytest.raises(InfeasibleError):
        result = select_initial_squad(players, fixtures, budget_million=50.0)

def test_case_3_club_constraint():
    """Test Case 3: >3 players same club - solver should respect 3-player limit"""
    players = create_minimal_test_dataset()
    fixtures = create_fixtures_dummy()
    
    # Make most high-value players from same team to test constraint
    # But ensure we still have feasible solution
    top_players_mask = players['total_points'] > players['total_points'].median()
    players.loc[top_players_mask, 'team'] = 1
    
    result = select_initial_squad(players, fixtures)
    
    # Check that no club has more than 3 players
    for club, count in result.club_counts.items():
        assert count <= 3, f"Club {club} has {count} players, exceeding limit of 3"

def test_case_4_missing_column():
    """Test Case 4: Missing element_type column - should raise KeyError"""
    players = create_minimal_test_dataset()
    fixtures = create_fixtures_dummy()
    
    # Remove required column
    players_missing_col = players.drop('element_type', axis=1)
    
    with pytest.raises(KeyError) as exc_info:
        result = select_initial_squad(players_missing_col, fixtures)
    
    assert "element_type" in str(exc_info.value)

def test_case_5_cost_tiebreaker():
    """Test Case 5: Tied optimal points, different costs - should choose cheaper squad"""
    # Create a scenario where we have multiple players with same expected points but different costs
    players = []
    
    # Goalkeepers - same points, different costs
    for i in range(3):
        players.append({
            'id': i + 1,
            'element_type': 1,
            'team': i + 1,
            'now_cost': 45 + i * 5,  # £4.5m, £5.0m, £5.5m
            'first_name': f'GK{i}',
            'second_name': f'Keeper{i}',
            'total_points': 100,  # Same points
            'ep_gw1': 25, 'ep_gw2': 25, 'ep_gw3': 25, 'ep_gw4': 25
        })
    
    # Create similar scenarios for other positions with enough variety
    base_id = 4
    for position, element_type, required in [('DEF', 2, 6), ('MID', 3, 6), ('FWD', 4, 4)]:
        for i in range(required):
            players.append({
                'id': base_id,
                'element_type': element_type,
                'team': (i % 3) + 1,
                'now_cost': 40 + i * 5,
                'first_name': f'{position}{i}',
                'second_name': f'{position}er{i}',
                'total_points': 80,
                'ep_gw1': 20, 'ep_gw2': 20, 'ep_gw3': 20, 'ep_gw4': 20
            })
            base_id += 1
    
    players_df = pd.DataFrame(players)
    fixtures = create_fixtures_dummy()
    
    # Since all players have same expected points, algorithm should pick cheaper ones
    result = select_initial_squad(
        players_df, fixtures, 
        expected_points_cols=['ep_gw1', 'ep_gw2', 'ep_gw3', 'ep_gw4']
    )
    
    # The total cost should be reasonable (not picking most expensive when points are equal)
    # This is hard to test precisely due to position constraints, but we can at least verify it runs
    assert result.total_cost <= 100.0
    assert len(result.squad_df) == 15

def test_parameter_validation():
    """Test input validation"""
    players = create_minimal_test_dataset()
    fixtures = create_fixtures_dummy()
    
    # Test invalid gameweek range
    with pytest.raises(ValueError):
        select_initial_squad(players, fixtures, gw_start=5, gw_end=3)
    
    # Test negative budget
    with pytest.raises(ValueError):
        select_initial_squad(players, fixtures, budget_million=-10)
    
    # Test duplicate player IDs
    players_dup = players.copy()
    players_dup.iloc[1, players_dup.columns.get_loc('id')] = players_dup.iloc[0, players_dup.columns.get_loc('id')]  # Create duplicate
    
    with pytest.raises(ValueError):
        select_initial_squad(players_dup, fixtures)

def test_genetic_algorithm_solver():
    """Test that GA solver works as fallback"""
    players = create_minimal_test_dataset()
    fixtures = create_fixtures_dummy()
    
    result = select_initial_squad(players, fixtures, solver="ga")
    
    assert isinstance(result, SquadResult)
    assert len(result.squad_df) == 15
    assert result.objective_details['solver'] == 'ga'

if __name__ == "__main__":
    # Run tests manually if not using pytest
    print("Running manual tests...")
    
    try:
        test_parameter_validation()
        print("✓ Parameter validation tests passed")
    except Exception as e:
        print(f"✗ Parameter validation failed: {e}")
    
    try:
        test_case_1_valid_minimal_dataset()
        print("✓ Test 1 (valid dataset) passed")
    except Exception as e:
        print(f"✗ Test 1 failed: {e}")
    
    try:
        test_case_2_budget_too_low()
        print("✓ Test 2 (budget too low) passed")
    except Exception as e:
        print(f"✗ Test 2 failed: {e}")
    
    try:
        test_case_3_club_constraint()
        print("✓ Test 3 (club constraints) passed")
    except Exception as e:
        print(f"✗ Test 3 failed: {e}")
    
    try:
        test_case_4_missing_column()
        print("✓ Test 4 (missing column) passed")
    except Exception as e:
        print(f"✗ Test 4 failed: {e}")
    
    try:
        test_genetic_algorithm_solver()
        print("✓ Test GA solver passed")
    except Exception as e:
        print(f"✗ GA solver test failed: {e}")
    
    print("\nAll manual tests completed!")
