"""
Demo script showing the FPL Squad Selection in action
"""
from main import select_initial_squad, load_fpl_data
import pandas as pd

def format_currency(value):
    """Format cost values as currency"""
    return f"£{value/10:.1f}m" if isinstance(value, (int, float)) else value

def main():
    print("🏆 FPL Squad Optimizer Demo")
    print("=" * 50)
    
    # Load real FPL data
    print("📥 Loading FPL data from API...")
    try:
        players_df, fixtures_df, _ = load_fpl_data()
        print(f"✓ Loaded {len(players_df)} players from {players_df['team'].nunique()} teams")
        
        # Show data overview
        print(f"\n📊 Player Distribution:")
        position_counts = players_df['position'].value_counts()
        for pos, count in position_counts.items():
            print(f"   {pos}: {count} players")
            
    except Exception as e:
        print(f"❌ Failed to load data: {e}")
        return
    
    # Run optimization
    print(f"\n🧮 Optimizing squad for GW1-4...")
    print("   Constraints: 2 GK, 5 DEF, 5 MID, 3 FWD | £100m budget | Max 3 per club")
    
    try:
        result = select_initial_squad(players_df, fixtures_df)
        
        print(f"\n✅ Optimization Complete!")
        print(f"   Total Cost: £{result.total_cost:.1f}m (Bank: £{100-result.total_cost:.1f}m)")
        print(f"   Expected Points (GW1-4): {result.expected_points:.1f}")
        print(f"   Solver: {result.objective_details.get('solver', 'unknown')}")
        
        # Show position breakdown
        print(f"\n📋 Position Breakdown:")
        for pos, player_ids in result.per_position.items():
            print(f"   {pos}: {len(player_ids)} players")
        
        # Show club distribution
        print(f"\n🏟️  Club Distribution:")
        club_dist = sorted(result.club_counts.items(), key=lambda x: x[1], reverse=True)
        for team_id, count in club_dist[:10]:  # Show top 10
            print(f"   Team {team_id}: {count} players")
        
        # Show fixture difficulty summary
        print(f"\n📅 Fixture Difficulty Summary (GW1-4):")
        if result.fixtures_info and result.fixtures_info.get('difficulty_summary'):
            for team_id, info in sorted(result.fixtures_info['difficulty_summary'].items(), 
                                      key=lambda x: x[1]['avg_difficulty']):
                avg_diff = info['avg_difficulty']
                total_diff = info['total_difficulty']
                print(f"   Team {team_id}: Avg {avg_diff:.1f} (Total: {total_diff})")
        
        # Show selected squad
        print(f"\n👥 Selected Squad:")
        print(f"{'Pos':<4} {'Name':<25} {'Team':<4} {'Cost':<8} {'Points':<8}")
        print("-" * 55)
        
        squad_display = result.squad_df.copy()
        squad_display['full_name'] = squad_display['first_name'] + ' ' + squad_display['second_name']
        squad_display['cost_formatted'] = squad_display['now_cost'].apply(format_currency)
        squad_display = squad_display.sort_values(['element_type', 'now_cost'], ascending=[True, False])
        
        for _, player in squad_display.iterrows():
            pos = player['position'][:3].upper()
            name = player['full_name'][:23] + '..' if len(player['full_name']) > 23 else player['full_name']
            team = str(player['team'])
            cost = player['cost_formatted']
            points = f"{player.get('exp_pts_window', 0):.1f}"
            
            print(f"{pos:<4} {name:<25} {team:<4} {cost:<8} {points:<8}")
        
        # Show detailed fixture information for top teams
        print(f"\n📅 Upcoming Fixtures (GW1-4) for Selected Teams:")
        if result.fixtures_info and result.fixtures_info.get('team_fixtures'):
            # Get teams with most players
            top_teams = sorted(result.club_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            for team_id, player_count in top_teams:
                if team_id in result.fixtures_info['team_fixtures']:
                    fixtures = result.fixtures_info['team_fixtures'][team_id]
                    fixture_str = " | ".join([f"GW{f['gameweek']}: vs{f['opponent']}({f['venue']}) D{f['difficulty']}" 
                                            for f in fixtures])
                    print(f"   Team {team_id} ({player_count} players): {fixture_str}")
        
        print(f"\n🎯 Pro Tips:")
        print(f"   • This squad maximizes expected points for the first 4 gameweeks")
        print(f"   • Consider captain choices from your highest expected scorers")
        print(f"   • Monitor injury news and price changes before the season starts")
        print(f"   • Plan your transfer strategy after GW4")
        
    except Exception as e:
        print(f"❌ Optimization failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
