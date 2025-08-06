"""
Demonstrate how fixture difficulty affects player weighting
"""
from main import select_initial_squad, load_fpl_data, _calculate_fixture_multiplier, _incorporate_fixture_difficulty
import pandas as pd
import numpy as np

def demonstrate_fixture_weighting():
    print("🔍 Fixture Difficulty Weighting Analysis")
    print("=" * 50)
    
    # Load data
    players_df, fixtures_df, _ = load_fpl_data()
    
    # Show how fixture difficulty affects a sample of players
    sample_players = players_df.head(10).copy()
    
    print("📊 Fixture Difficulty Multipliers for GW1:")
    print("=" * 50)
    
    # Calculate multipliers for GW1
    gw1_multipliers = _calculate_fixture_multiplier(sample_players, fixtures_df, 1)
    
    # Show the multiplier logic
    print("Multiplier Logic:")
    print("• Difficulty 1 (easiest) → ×1.4 (40% boost)")
    print("• Difficulty 2 → ×1.2 (20% boost)")  
    print("• Difficulty 3 → ×1.0 (neutral)")
    print("• Difficulty 4 → ×0.8 (20% penalty)")
    print("• Difficulty 5 (hardest) → ×0.6 (40% penalty)")
    print()
    
    # Show actual multipliers for sample players
    print(f"{'Player':<25} {'Team':<6} {'Base Pts':<10} {'Multiplier':<12} {'Adjusted Pts':<12}")
    print("-" * 75)
    
    for idx, (_, player) in enumerate(sample_players.iterrows()):
        base_points = player.get('total_points', 100) / 38  # Base points per GW
        multiplier = gw1_multipliers.iloc[idx]
        adjusted_points = base_points * multiplier
        
        player_name = f"{player.get('first_name', '')} {player.get('second_name', 'Unknown')}"[:24]
        
        print(f"{player_name:<25} {player['team']:<6} {base_points:<10.1f} {multiplier:<12.2f} {adjusted_points:<12.1f}")
    
    print("\n" + "=" * 50)
    print("🎯 Impact on Squad Selection:")
    
    # Run optimization and show how fixture difficulty influenced selection
    result = select_initial_squad(players_df, fixtures_df)
    
    # Show teams selected and their fixture difficulties
    if result.fixtures_info and 'difficulty_summary' in result.fixtures_info:
        print(f"\n{'Team':<6} {'Players':<8} {'Avg Difficulty':<15} {'Expected Impact'}")
        print("-" * 50)
        
        for team_id, info in sorted(result.fixtures_info['difficulty_summary'].items(), 
                                  key=lambda x: x[1]['avg_difficulty']):
            player_count = result.club_counts.get(team_id, 0)
            avg_diff = info['avg_difficulty']
            
            if avg_diff < 2.5:
                impact = "📈 Boosted (easy fixtures)"
            elif avg_diff > 3.5:
                impact = "📉 Penalized (hard fixtures)"
            else:
                impact = "⚖️ Neutral"
            
            print(f"{team_id:<6} {player_count:<8} {avg_diff:<15.1f} {impact}")
    
    print("\n💡 Key Insights:")
    print("• Players from teams with easier fixtures get higher expected points")
    print("• This makes them more likely to be selected by the optimizer")
    print("• The algorithm automatically favors good fixtures over star names")
    print("• Multipliers are applied to each gameweek individually")

def compare_with_without_fixtures():
    """Compare squad selection with and without fixture consideration"""
    print("\n" + "=" * 50)
    print("⚖️ Comparing Selection With vs Without Fixtures")
    print("=" * 50)
    
    players_df, fixtures_df, _ = load_fpl_data()
    
    # Selection WITH fixtures (current implementation)
    result_with = select_initial_squad(players_df, fixtures_df)
    
    # Selection WITHOUT fixtures (empty fixtures DataFrame)
    empty_fixtures = pd.DataFrame()
    result_without = select_initial_squad(players_df, empty_fixtures)
    
    print(f"📊 Results Comparison:")
    print(f"With Fixtures:    £{result_with.total_cost:.1f}m, {result_with.expected_points:.1f} pts")
    print(f"Without Fixtures: £{result_without.total_cost:.1f}m, {result_without.expected_points:.1f} pts")
    print(f"Difference:       {result_with.expected_points - result_without.expected_points:+.1f} pts")
    
    # Show which teams were preferred
    print(f"\n📈 Teams Most Selected (With Fixtures):")
    with_teams = sorted(result_with.club_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    for team, count in with_teams:
        print(f"   Team {team}: {count} players")
    
    print(f"\n📊 Teams Most Selected (Without Fixtures):")  
    without_teams = sorted(result_without.club_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    for team, count in without_teams:
        print(f"   Team {team}: {count} players")

def show_fixture_multiplier_examples():
    """Show concrete examples of how multipliers work"""
    print("\n" + "=" * 50)
    print("🔢 Concrete Multiplier Examples")
    print("=" * 50)
    
    difficulties = [1, 2, 3, 4, 5]
    
    print("Fixture Difficulty → Points Multiplier:")
    for diff in difficulties:
        multiplier = max(0.6, 1.6 - (diff * 0.2))
        change = (multiplier - 1.0) * 100
        
        if change > 0:
            direction = f"+{change:.0f}% boost"
        elif change < 0:
            direction = f"{change:.0f}% penalty"
        else:
            direction = "neutral"
            
        print(f"   Difficulty {diff} → ×{multiplier:.1f} ({direction})")
    
    print("\nReal Example:")
    print("📋 Player A: Base 2.5 pts/GW, facing difficulty 2 opponent")
    print(f"   → Adjusted: 2.5 × 1.2 = {2.5 * 1.2:.1f} pts/GW")
    
    print("📋 Player B: Base 2.5 pts/GW, facing difficulty 4 opponent")
    print(f"   → Adjusted: 2.5 × 0.8 = {2.5 * 0.8:.1f} pts/GW")
    
    print("\n💡 Player A becomes 50% more valuable than Player B due to fixtures!")

if __name__ == "__main__":
    demonstrate_fixture_weighting()
    compare_with_without_fixtures()
    show_fixture_multiplier_examples()