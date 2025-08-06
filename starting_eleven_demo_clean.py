"""
Clean demo of FPL Starting Eleven Selection
"""

from main import select_initial_squad, select_starting_eleven, load_fpl_data

def demo_starting_eleven():
    """Demonstrate the starting eleven selection functionality"""
    print("🏆 FPL Starting Eleven Optimizer Demo")
    print("=" * 50)
    
    # Load FPL data
    print("📥 Loading FPL data...")
    players, fixtures, data = load_fpl_data()
    
    # Select optimal squad
    print("📊 Selecting optimal 15-player squad...")
    squad_result = select_initial_squad(players, fixtures)
    print(f"✅ Squad Selected: £{squad_result.total_cost:.1f}m, {squad_result.expected_points:.1f} total points (GW1-4)")
    
    # Select starting eleven for GW1
    print("\n🎯 Optimizing Starting XI for Gameweek 1...")
    allowed_formations = ['3-4-3', '3-5-2', '4-3-3', '4-4-2', '4-5-1', '5-2-3', '5-3-2', '5-4-1']
    print(f"Allowed formations: {', '.join(allowed_formations)}")
    
    result = select_starting_eleven(squad_result, gameweek=1)
    
    # Get captain and vice captain names for display
    captain_name = result.starting_eleven[result.starting_eleven['id'] == result.captain_id]['web_name'].iloc[0]
    vice_captain_name = result.starting_eleven[result.starting_eleven['id'] == result.vice_captain_id]['web_name'].iloc[0]
    
    print(f"\n⭐ Optimal Formation: {result.formation}")
    print(f"Expected Points GW1: {result.expected_points_gw1:.1f} (including captain double points)")
    
    # Display starting XI by position
    print(f"\n👥 Starting XI ({result.formation}):")
    print("=" * 70)
    
    # Get position counts for the formation
    def_count, mid_count, fwd_count = map(int, result.formation.split('-'))
    
    # Group players by position
    positions = {'GK': [], 'DEF': [], 'MID': [], 'FWD': []}
    for _, player in result.starting_eleven.iterrows():
        pos = player['position']
        positions[pos].append(player)
    
    # Display each position
    position_names = {'GK': 'Goalkeeper', 'DEF': 'Defender', 'MID': 'Midfielder', 'FWD': 'Forward'}
    expected_counts = {'GK': 1, 'DEF': def_count, 'MID': mid_count, 'FWD': fwd_count}
    
    for pos_code in ['GK', 'DEF', 'MID', 'FWD']:
        players = positions[pos_code]
        if players:
            print(f"{position_names[pos_code]} ({expected_counts[pos_code]} players):")
            for player in players:
                captain_info = ""
                if player['id'] == result.captain_id:
                    captain_info = f" → {player['ep_gw1'] * 2:.1f} pts (C) 👨‍✈️"
                elif player['id'] == result.vice_captain_id:
                    captain_info = f" (VC) 🏃‍♂️"
                    
                print(f"   • {player['web_name']:<20} £{player['now_cost']/10:.1f}m    {player['ep_gw1']:.1f} pts{captain_info}")
    
    # Display bench
    print(f"\n🪑 Bench ({len(result.bench)} players):")
    print("=" * 40)
    for i, (_, player) in enumerate(result.bench.iterrows(), 1):
        print(f"   {i}. {player['web_name']:<20} {player['position']} £{player['now_cost']/10:.1f}m    {player['ep_gw1']:.1f} pts")
    
    # Captain analysis
    print(f"\n👨‍✈️ Captain Analysis:")
    print("=" * 25)
    print(f"{'Player':<25} {'GW1 Points':<12} {'Captain Points':<15} {'Status'}")
    print("-" * 60)
    
    # Show top 3 captain candidates
    captain_candidates = result.starting_eleven.nlargest(3, 'ep_gw1')
    for _, player in captain_candidates.iterrows():
        captain_points = player['ep_gw1'] * 2
        if player['id'] == result.captain_id:
            status = "✅ CAPTAIN"
        elif player['id'] == result.vice_captain_id:
            status = "🏃‍♂️ VICE-CAP"
        else:
            status = "⚪ Candidate"
        
        print(f"{player['web_name']:<25} {player['ep_gw1']:<12.1f} {captain_points:<15.1f} {status}")
    
    # Key insights
    captain_bonus = result.starting_eleven[result.starting_eleven['id'] == result.captain_id]['ep_gw1'].iloc[0]
    bench_total = result.bench['ep_gw1'].sum()
    
    print(f"\n💡 Key Insights:")
    print(f"• Formation {result.formation} maximizes GW1 expected points")
    print(f"• Captain choice adds {captain_bonus:.1f} extra points")
    print(f"• Starting XI uses players from {len(positions)} different positions")
    print(f"• Bench provides {bench_total:.1f} total backup points")

if __name__ == "__main__":
    demo_starting_eleven()
