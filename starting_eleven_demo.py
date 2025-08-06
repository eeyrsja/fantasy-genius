"""
Demo script showing starting eleven selection for GW1
"""
from main import select_initial_squad, load_fpl_data, select_starting_eleven

def demo_starting_eleven():
    print("🏆 FPL Starting Eleven Optimizer Demo")
    print("=" * 50)
    
    # Load data and select initial squad
    print("📥 Loading FPL data and selecting optimal 15-player squad...")
    players_df, fixtures_df, _ = load_fpl_data()
    squad_result = select_initial_squad(players_df, fixtures_df)
    
    print(f"✅ Squad Selected: £{squad_result.total_cost:.1f}m, {squad_result.expected_points:.1f} total points (GW1-4)")
    
    # Select starting eleven for GW1
    print(f"\n🎯 Optimizing Starting XI for Gameweek 1...")
    print("Allowed formations: 3-4-3, 3-5-2, 4-3-3, 4-4-2, 4-5-1, 5-2-3, 5-3-2, 5-4-1")
    
    starting_result = select_starting_eleven(squad_result, gameweek=1)
    
    print(f"\n⭐ Optimal Formation: {starting_result.formation}")
    print(f"Expected Points GW1: {starting_result.expected_points_gw1:.1f} (including captain double points)")
    
    # Display starting XI by position
    print(f"\n👥 Starting XI ({starting_result.formation}):")
    print("=" * 70)
    
    positions_order = ['GK', 'DEF', 'MID', 'FWD']
    
    for position in positions_order:
        position_players = starting_result.starting_eleven[
            starting_result.starting_eleven['position'] == position
        ].sort_values('ep_gw1', ascending=False)
        
        if not position_players.empty:
            pos_name = {'GK': 'Goalkeeper', 'DEF': 'Defender', 'MID': 'Midfielder', 'FWD': 'Forward'}[position]
            print(f"\n{pos_name} ({len(position_players)} players):")
            
            for _, player in position_players.iterrows():
                name = f"{player.get('first_name', '')} {player.get('second_name', 'Unknown')}"
                cost = f"£{player['now_cost']/10:.1f}m"
                points = f"{player['ep_gw1']:.1f} pts"
                
                # Add captain/vice-captain indicators
                if player['id'] == starting_result.captain_id:
                    role = " (C) 👨‍✈️"
                    points += f" → {player['ep_gw1']*2:.1f} pts"
                elif player['id'] == starting_result.vice_captain_id:
                    role = " (VC) 🏃‍♂️"
                else:
                    role = ""
                
                print(f"   • {name:<25} {cost:<8} {points}{role}")
    
    # Show bench
    print(f"\n🪑 Bench (4 players):")
    print("=" * 40)
    
    bench_sorted = starting_result.bench.sort_values('ep_gw1', ascending=False)
    for i, (_, player) in enumerate(bench_sorted.iterrows(), 1):
        name = f"{player.get('first_name', '')} {player.get('second_name', 'Unknown')}"
        pos = player['position'][:3].upper()
        cost = f"£{player['now_cost']/10:.1f}m"
        points = f"{player['ep_gw1']:.1f} pts"
        print(f"   {i}. {name:<25} {pos} {cost:<8} {points}")
    
    # Show alternative formations analysis
    print(f"\n📊 Formation Analysis:")
    print("=" * 30)
    
    formations_to_try = [(3,4,3), (4,3,3), (4,4,2), (3,5,2), (5,3,2)]
    
    print(f"{'Formation':<10} {'Expected Points':<15} {'Status'}")
    print("-" * 35)
    
    for def_count, mid_count, fwd_count in formations_to_try:
        formation_str = f"{def_count}-{mid_count}-{fwd_count}"
        try:
            temp_result = select_starting_eleven(squad_result, gameweek=1)
            if temp_result.formation == formation_str:
                status = "✅ SELECTED"
                points = temp_result.expected_points_gw1
            else:
                # Try to estimate points for this formation (simplified)
                from main import _optimize_formation
                try:
                    _, _, points, _, _ = _optimize_formation(
                        squad_result.squad_df, def_count, mid_count, fwd_count, 'ep_gw1', 2.0, 1.0
                    )
                    status = "⚪ Alternative"
                except:
                    points = 0
                    status = "❌ Invalid"
        except:
            points = 0
            status = "❌ Invalid"
        
        print(f"{formation_str:<10} {points:<15.1f} {status}")
    
    # Show captain analysis
    print(f"\n👨‍✈️ Captain Analysis:")
    print("=" * 25)
    
    # Get top 3 captain candidates
    captain_candidates = starting_result.starting_eleven.nlargest(3, 'ep_gw1')
    
    print(f"{'Player':<25} {'GW1 Points':<12} {'Captain Points':<15} {'Status'}")
    print("-" * 60)
    
    for _, player in captain_candidates.iterrows():
        name = f"{player.get('first_name', '')} {player.get('second_name', 'Unknown')}"[:24]
        base_points = player['ep_gw1']
        captain_points = base_points * 2
        
        if player['id'] == starting_result.captain_id:
            status = "✅ CAPTAIN"
        elif player['id'] == starting_result.vice_captain_id:
            status = "🏃‍♂️ VICE-CAP"
        else:
            status = "⚪ Candidate"
        
        print(f"{name:<25} {base_points:<12.1f} {captain_points:<15.1f} {status}")
    
    print(f"\n💡 Key Insights:")
    print(f"• Formation {starting_result.formation} maximizes GW1 expected points")
    print(f"• Captain choice adds {starting_result.expected_points_gw1 - (starting_result.starting_eleven['ep_gw1'].sum() + starting_result.starting_eleven.nlargest(1, 'ep_gw1')['ep_gw1'].iloc[0]):.1f} extra points")
    print(f"• {len([p for p in positions_order if len(starting_result.starting_eleven[starting_result.starting_eleven['position'] == p]) > 0])} different positions represented")
    print(f"• Bench provides {starting_result.bench['ep_gw1'].sum():.1f} total backup points")

if __name__ == "__main__":
    demo_starting_eleven()
