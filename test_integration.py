"""
Simple integration test using real FPL data
"""
from main import select_initial_squad, load_fpl_data
import pandas as pd

def test_with_real_data():
    """Test with actual FPL data (subset)"""
    print("Loading real FPL data...")
    players_df, fixtures_df, _ = load_fpl_data()
    
    print(f"Loaded {len(players_df)} players")
    
    # Test with a subset to make it faster
    # Take top players from each position to ensure quality
    subset_players = []
    
    for element_type in [1, 2, 3, 4]:  # GK, DEF, MID, FWD
        position_players = players_df[players_df['element_type'] == element_type]
        # Sort by total points and take diverse teams
        position_players = position_players.sort_values('total_points', ascending=False)
        
        # Take top players ensuring team diversity
        selected_count = 0
        team_counts = {}
        max_per_position = {1: 8, 2: 25, 3: 30, 4: 15}  # Generous limits
        
        for idx, player in position_players.iterrows():
            team = player['team']
            if team_counts.get(team, 0) < 5 and selected_count < max_per_position[element_type]:
                subset_players.append(player)
                team_counts[team] = team_counts.get(team, 0) + 1
                selected_count += 1
    
    subset_df = pd.DataFrame(subset_players)
    
    print(f"Testing with subset of {len(subset_df)} players")
    print("Position distribution:", subset_df['element_type'].value_counts().sort_index())
    
    # Test the algorithm
    try:
        result = select_initial_squad(subset_df, fixtures_df)
        
        print(f"\n✓ Success! Selected squad:")
        print(f"Total cost: £{result.total_cost:.1f}m (budget: £100.0m)")
        print(f"Expected points: {result.expected_points:.1f}")
        print(f"Position breakdown: {result.per_position}")
        print(f"Club distribution: {result.club_counts}")
        
        # Verify constraints
        assert len(result.squad_df) == 15
        assert result.total_cost <= 100.0
        assert max(result.club_counts.values()) <= 3
        assert len(result.per_position['GK']) == 2
        assert len(result.per_position['DEF']) == 5
        assert len(result.per_position['MID']) == 5
        assert len(result.per_position['FWD']) == 3
        
        print("✓ All constraints satisfied!")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_with_real_data()
    print(f"\nIntegration test: {'PASSED' if success else 'FAILED'}")
