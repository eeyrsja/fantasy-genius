"""
Example showing fixture analysis capabilities
"""
from main import select_initial_squad, load_fpl_data

def analyze_fixtures():
    print("🔍 FPL Fixture Analysis Demo")
    print("=" * 40)
    
    # Load data
    players_df, fixtures_df, _ = load_fpl_data()
    
    # Select optimal squad
    result = select_initial_squad(players_df, fixtures_df)
    
    print(f"\n📊 Squad Overview:")
    print(f"Total Cost: £{result.total_cost:.1f}m")
    print(f"Expected Points (fixture-adjusted): {result.expected_points:.1f}")
    
    # Show fixture difficulty weighting explanation
    print(f"\n🎯 Fixture Difficulty Weighting:")
    print(f"   • Difficulty 1 (easiest) → ×1.4 (40% points boost)")
    print(f"   • Difficulty 2 → ×1.2 (20% points boost)")
    print(f"   • Difficulty 3 → ×1.0 (neutral)")
    print(f"   • Difficulty 4 → ×0.8 (20% points penalty)")
    print(f"   • Difficulty 5 (hardest) → ×0.6 (40% points penalty)")
    
    # Analyze fixture difficulty impact
    print(f"\n📅 Fixture Difficulty Analysis:")
    if result.fixtures_info and result.fixtures_info.get('difficulty_summary'):
        print(f"{'Team':<6} {'Players':<8} {'Avg Diff':<10} {'Points Impact':<15} {'GW1-4 Fixtures'}")
        print("-" * 85)
        
        for team_id, info in sorted(result.fixtures_info['difficulty_summary'].items(), 
                                  key=lambda x: x[1]['avg_difficulty']):
            player_count = result.club_counts.get(team_id, 0)
            avg_diff = info['avg_difficulty']
            
            # Determine points impact based on average difficulty
            if avg_diff < 2.5:
                impact = "📈 Boosted"
            elif avg_diff > 3.5:
                impact = "📉 Penalized"  
            else:
                impact = "⚖️ Neutral"
            
            # Format fixtures string
            fixtures_str = " | ".join([
                f"vs{f['opponent']}({f['venue']})D{f['difficulty']}" 
                for f in info['fixtures']
            ])
            
            print(f"{team_id:<6} {player_count:<8} {avg_diff:<10.1f} {impact:<15} {fixtures_str}")
    
    # Show teams with best fixtures (lowest difficulty)
    if result.fixtures_info and result.fixtures_info.get('difficulty_summary'):
        easiest_fixtures = sorted(
            result.fixtures_info['difficulty_summary'].items(), 
            key=lambda x: x[1]['avg_difficulty']
        )[:3]
        
        print(f"\n🌟 Teams with Easiest Fixtures (Selected):")
        for team_id, info in easiest_fixtures:
            player_count = result.club_counts.get(team_id, 0)
            print(f"   Team {team_id}: {player_count} players, Avg difficulty {info['avg_difficulty']:.1f}")
    
    print(f"\n💡 Fixture Impact:")
    print(f"   • Easier fixtures (lower difficulty) = higher expected points")
    print(f"   • The optimizer considers fixture difficulty when selecting players")
    print(f"   • Teams facing weaker opponents get a points boost in the calculation")
    
    # Add concrete example showing fixture weighting in action
    print(f"\n🔢 Fixture Weighting Examples:")
    print(f"   Example: Two identical £6.0m midfielders")
    print(f"   • Player A (Team with difficulty 2 fixtures): Base 2.5 pts → 2.5 × 1.2 = 3.0 pts")
    print(f"   • Player B (Team with difficulty 4 fixtures): Base 2.5 pts → 2.5 × 0.8 = 2.0 pts")
    print(f"   • Result: Player A is 50% more likely to be selected!")
    
    print(f"\n📈 Why This Matters:")
    print(f"   • Fixture difficulty makes average players from good teams more valuable")
    print(f"   • Elite players from teams with tough fixtures may be overlooked")
    print(f"   • The algorithm balances player quality vs fixture quality")
    print(f"   • This mirrors real FPL strategy - target teams with good fixtures!")

if __name__ == "__main__":
    analyze_fixtures()
