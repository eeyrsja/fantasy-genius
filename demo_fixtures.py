"""
Simple demo to test and showcase fixture weighting
"""
from main import select_initial_squad, load_fpl_data

def demo_fixture_weighting():
    print("🔍 Fixture Weighting Demo")
    print("=" * 40)
    
    # Load FPL data
    players_df, fixtures_df, _ = load_fpl_data()
    
    print(f"Data loaded: {len(players_df)} players, {len(fixtures_df)} fixtures")
    
    # Run squad selection
    print("\n🎯 Running squad selection with fixture weighting...")
    result = select_initial_squad(players_df, fixtures_df)
    
    print(f"\n📊 Results:")
    print(f"Total Cost: £{result.total_cost:.1f}m")
    print(f"Expected Points: {result.expected_points:.1f}")
    
    # Show fixture information if available
    if result.fixtures_info and 'difficulty_summary' in result.fixtures_info:
        print(f"\n📅 Team Fixture Difficulties (GW1-4):")
        print(f"{'Team':<6} {'Players':<8} {'Avg Difficulty':<15}")
        print("-" * 35)
        
        for team_id, info in sorted(result.fixtures_info['difficulty_summary'].items(), 
                                  key=lambda x: x[1]['avg_difficulty']):
            player_count = result.club_counts.get(team_id, 0)
            avg_diff = info['avg_difficulty']
            print(f"{team_id:<6} {player_count:<8} {avg_diff:<15.1f}")
        
        # Show teams with easiest fixtures
        easiest_teams = sorted(result.fixtures_info['difficulty_summary'].items(), 
                             key=lambda x: x[1]['avg_difficulty'])[:3]
        
        print(f"\n🌟 Teams with Easiest Fixtures (most likely to have players selected):")
        for team_id, info in easiest_teams:
            player_count = result.club_counts.get(team_id, 0)
            print(f"   Team {team_id}: {player_count} players selected, avg difficulty {info['avg_difficulty']:.1f}")
    
    print(f"\n💡 How Fixture Weighting Works:")
    print(f"   • Difficulty 1 (easiest) → ×1.4 multiplier (40% points boost)")
    print(f"   • Difficulty 2 → ×1.2 multiplier (20% points boost)")
    print(f"   • Difficulty 3 → ×1.0 multiplier (neutral)")
    print(f"   • Difficulty 4 → ×0.8 multiplier (20% points penalty)")
    print(f"   • Difficulty 5 (hardest) → ×0.6 multiplier (40% points penalty)")
    
    print(f"\n📈 Result: Teams with easier fixtures have more players selected!")

if __name__ == "__main__":
    demo_fixture_weighting()