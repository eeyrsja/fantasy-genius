"""
Test script to verify fixture difficulty is being applied
"""
from main import select_initial_squad, load_fpl_data, _calculate_fixture_multiplier

def test_fixture_application():
    print("🧪 Testing Fixture Difficulty Application")
    print("=" * 50)
    
    # Load data
    players_df, fixtures_df, _ = load_fpl_data()
    
    print(f"Loaded {len(fixtures_df)} fixtures")
    print(f"Fixtures columns: {list(fixtures_df.columns)}")
    
    # Test fixture multiplier calculation for GW1
    sample_players = players_df.head(10)
    
    print("\n📊 GW1 Fixture Multiplier Test:")
    if not fixtures_df.empty and 'event' in fixtures_df.columns:
        gw1_multipliers = _calculate_fixture_multiplier(sample_players, fixtures_df, 1)
        
        print(f"{'Player':<25} {'Team':<6} {'Total Pts':<10} {'Base/GW':<10} {'Multiplier':<12} {'Adjusted':<10}")
        print("-" * 85)
        
        for idx, (_, player) in enumerate(sample_players.iterrows()):
            total_pts = player.get('total_points', 50)
            base_per_gw = total_pts / 38
            multiplier = gw1_multipliers.iloc[idx]
            adjusted = base_per_gw * multiplier
            
            player_name = f"{player.get('first_name', '')} {player.get('second_name', 'Unknown')}"[:24]
            
            print(f"{player_name:<25} {player['team']:<6} {total_pts:<10} {base_per_gw:<10.1f} {multiplier:<12.2f} {adjusted:<10.1f}")
    else:
        print("❌ No fixture data available")
        return
    
    print("\n🎯 Testing Squad Selection with Fixtures:")
    
    # Compare with and without fixtures
    result_with_fixtures = select_initial_squad(players_df, fixtures_df)
    
    empty_fixtures = fixtures_df.iloc[0:0].copy()  # Empty DataFrame with same structure
    result_without_fixtures = select_initial_squad(players_df, empty_fixtures)
    
    print(f"\nResults Comparison:")
    print(f"With Fixtures:    £{result_with_fixtures.total_cost:.1f}m, {result_with_fixtures.expected_points:.1f} pts")
    print(f"Without Fixtures: £{result_without_fixtures.total_cost:.1f}m, {result_without_fixtures.expected_points:.1f} pts")
    print(f"Difference:       {result_with_fixtures.expected_points - result_without_fixtures.expected_points:+.1f} pts")
    
    if abs(result_with_fixtures.expected_points - result_without_fixtures.expected_points) > 0.1:
        print("✅ Fixture difficulty is being applied correctly!")
    else:
        print("⚠️ Fixture difficulty may not be working - results are identical")

if __name__ == "__main__":
    test_fixture_application()