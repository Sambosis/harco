#!/usr/bin/env python3
"""
demo_visualization.py

Standalone demonstration of the Harford County Clash visualization system.

This script creates a simulated game scenario to showcase:
- Enhanced terminal display with colors and unit movements
- Turn-by-turn action tracking
- Battle animations and results
- Replay file generation

Run with: python demo_visualization.py [--web] [--web-port 8080]
"""

import argparse
import time
from typing import Dict, Any, List
import sys
import os

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game_state import GameState, Unit, Coord, Tile
from visualizer import GameVisualizer


def create_demo_game_state() -> GameState:
    """Create a sample game state for demonstration."""
    
    # Create a simple 10x10 grid with some terrain variety
    tiles = []
    for y in range(10):
        for x in range(10):
            if x == 0 or x == 9 or y == 0 or y == 9:
                terrain = "water" if (x + y) % 4 == 0 else "forest"
            elif x in [3, 6] and y in [3, 6]:
                terrain = "urban"
            else:
                terrain = "rural"
            
            name = f"Tile_{x}_{y}"
            tiles.append(Tile(
                coord=Coord(x, y),
                name=name,
                terrain_type=terrain,
                traversable=terrain != "water"
            ))
    
    # Create team headquarters
    team_hqs = {
        "BlueCrabs": Coord(2, 2),
        "BayBirds": Coord(7, 7)
    }
    
    # Create units for both teams
    units = {
        "BlueCrabs-1": Unit("BlueCrabs-1", "BlueCrabs", Coord(1, 2), 10, 5),
        "BlueCrabs-2": Unit("BlueCrabs-2", "BlueCrabs", Coord(2, 1), 10, 5),
        "BlueCrabs-3": Unit("BlueCrabs-3", "BlueCrabs", Coord(3, 2), 10, 5),
        "BayBirds-1": Unit("BayBirds-1", "BayBirds", Coord(8, 7), 10, 5),
        "BayBirds-2": Unit("BayBirds-2", "BayBirds", Coord(7, 8), 10, 5),
        "BayBirds-3": Unit("BayBirds-3", "BayBirds", Coord(6, 7), 10, 5),
    }
    
    return GameState(
        tiles=tiles,
        units=units,
        team_hqs=team_hqs,
        turn_counter=0
    )


def simulate_game_turn(visualizer: GameVisualizer, game_state: GameState, turn: int) -> GameState:
    """Simulate a single turn with realistic actions."""
    
    visualizer.begin_turn(turn)
    
    # Simulate some movements and attacks
    if turn == 1:
        # Turn 1: Initial movements
        visualizer.record_action("BlueCrabs-1", "move", Coord(1, 2), Coord(2, 2), success=True)
        visualizer.record_action("BlueCrabs-2", "move", Coord(2, 1), Coord(3, 1), success=True)
        visualizer.record_action("BlueCrabs-3", "pass", Coord(3, 2), success=True)
        
        visualizer.record_action("BayBirds-1", "move", Coord(8, 7), Coord(7, 7), success=True)
        visualizer.record_action("BayBirds-2", "move", Coord(7, 8), Coord(6, 8), success=True)
        visualizer.record_action("BayBirds-3", "move", Coord(6, 7), Coord(5, 7), success=True)
        
        # Update positions
        game_state.units["BlueCrabs-1"].coord = Coord(2, 2)
        game_state.units["BlueCrabs-2"].coord = Coord(3, 1)
        game_state.units["BayBirds-1"].coord = Coord(7, 7)
        game_state.units["BayBirds-2"].coord = Coord(6, 8)
        game_state.units["BayBirds-3"].coord = Coord(5, 7)
        
    elif turn == 2:
        # Turn 2: Advance towards center
        visualizer.record_action("BlueCrabs-1", "move", Coord(2, 2), Coord(3, 2), success=True)
        visualizer.record_action("BlueCrabs-2", "move", Coord(3, 1), Coord(4, 1), success=True)
        visualizer.record_action("BlueCrabs-3", "move", Coord(3, 2), Coord(4, 2), success=True)
        
        visualizer.record_action("BayBirds-1", "move", Coord(7, 7), Coord(6, 7), success=True)
        visualizer.record_action("BayBirds-2", "move", Coord(6, 8), Coord(5, 8), success=True)
        visualizer.record_action("BayBirds-3", "move", Coord(5, 7), Coord(4, 7), success=True)
        
        # Update positions
        game_state.units["BlueCrabs-1"].coord = Coord(3, 2)
        game_state.units["BlueCrabs-2"].coord = Coord(4, 1)
        game_state.units["BlueCrabs-3"].coord = Coord(4, 2)
        game_state.units["BayBirds-1"].coord = Coord(6, 7)
        game_state.units["BayBirds-2"].coord = Coord(5, 8)
        game_state.units["BayBirds-3"].coord = Coord(4, 7)
        
    elif turn == 3:
        # Turn 3: First combat!
        visualizer.record_action("BlueCrabs-1", "move", Coord(3, 2), Coord(4, 3), success=True)
        visualizer.record_action("BlueCrabs-2", "move", Coord(4, 1), Coord(4, 2), success=True)
        visualizer.record_action("BlueCrabs-3", "attack", Coord(4, 2), Coord(4, 7), "BayBirds-3", 5, success=True)
        
        visualizer.record_action("BayBirds-1", "move", Coord(6, 7), Coord(5, 7), success=True)
        visualizer.record_action("BayBirds-2", "move", Coord(5, 8), Coord(4, 8), success=True)
        visualizer.record_action("BayBirds-3", "attack", Coord(4, 7), Coord(4, 2), "BlueCrabs-3", 5, success=True)
        
        # Update positions and damage
        game_state.units["BlueCrabs-1"].coord = Coord(4, 3)
        game_state.units["BlueCrabs-2"].coord = Coord(4, 2)
        game_state.units["BlueCrabs-3"].hp = 5  # Took damage
        game_state.units["BayBirds-1"].coord = Coord(5, 7)
        game_state.units["BayBirds-2"].coord = Coord(4, 8)
        game_state.units["BayBirds-3"].hp = 5  # Took damage
        
    elif turn == 4:
        # Turn 4: Continued fighting
        visualizer.record_action("BlueCrabs-1", "attack", Coord(4, 3), Coord(4, 2), "BlueCrabs-2", 0, success=False)  # Friendly fire attempt
        visualizer.record_action("BlueCrabs-2", "move", Coord(4, 2), Coord(5, 2), success=True)
        visualizer.record_action("BlueCrabs-3", "attack", Coord(4, 2), Coord(4, 7), "BayBirds-3", 5, success=True)
        
        visualizer.record_action("BayBirds-1", "move", Coord(5, 7), Coord(4, 6), success=True)
        visualizer.record_action("BayBirds-2", "attack", Coord(4, 8), Coord(4, 7), "BayBirds-3", 0, success=False)  # Friendly fire attempt
        visualizer.record_action("BayBirds-3", "move", Coord(4, 7), Coord(3, 7), success=True)
        
        # Update state - BayBirds-3 is eliminated
        game_state.units["BlueCrabs-2"].coord = Coord(5, 2)
        game_state.units["BayBirds-1"].coord = Coord(4, 6)
        game_state.units["BayBirds-3"].coord = Coord(3, 7)
        game_state.units["BayBirds-3"].hp = 0  # Eliminated!
        
    elif turn == 5:
        # Turn 5: BlueCrabs advance toward BayBirds HQ
        visualizer.record_action("BlueCrabs-1", "move", Coord(4, 3), Coord(5, 3), success=True)
        visualizer.record_action("BlueCrabs-2", "move", Coord(5, 2), Coord(6, 2), success=True)
        visualizer.record_action("BlueCrabs-3", "move", Coord(4, 2), Coord(5, 1), success=True)
        
        visualizer.record_action("BayBirds-1", "move", Coord(4, 6), Coord(5, 6), success=True)
        visualizer.record_action("BayBirds-2", "move", Coord(4, 8), Coord(5, 8), success=True)
        
        # Update positions
        game_state.units["BlueCrabs-1"].coord = Coord(5, 3)
        game_state.units["BlueCrabs-2"].coord = Coord(6, 2)
        game_state.units["BlueCrabs-3"].coord = Coord(5, 1)
        game_state.units["BayBirds-1"].coord = Coord(5, 6)
        game_state.units["BayBirds-2"].coord = Coord(5, 8)
    
    # Increment turn counter
    game_state.turn_counter = turn
    
    # End the turn
    visualizer.end_turn(game_state)
    
    return game_state


def run_demo(enable_web: bool = False, web_port: int = 8080):
    """Run the visualization demo."""
    
    print("🎮 HARFORD COUNTY CLASH - VISUALIZATION DEMO")
    print("=" * 60)
    print()
    print("This demo showcases the visual display system with a")
    print("simulated battle between BlueCrabs and BayBirds!")
    print()
    
    if enable_web:
        print(f"🌐 Web interface will be available at: http://localhost:{web_port}")
        print("   (Open this URL in your browser after the demo starts)")
        print()
    
    print("Press Enter to start the demo...")
    input()
    
    # Initialize the visualizer
    visualizer = GameVisualizer(
        enable_terminal_display=True,
        enable_web_interface=enable_web,
        web_port=web_port,
        save_replay=True,
        replay_file="demo_replay.json"
    )
    
    # Create initial game state
    game_state = create_demo_game_state()
    visualizer.initialize_game(game_state)
    
    print("\nStarting 5-turn battle simulation...")
    print("(Each turn will pause for 3 seconds to show the action)")
    print()
    
    # Simulate 5 turns of gameplay
    for turn in range(1, 6):
        print(f"⏱️  Starting Turn {turn}...")
        game_state = simulate_game_turn(visualizer, game_state, turn)
        
        if turn < 5:  # Don't wait after the last turn
            time.sleep(3)
    
    # End the game
    print("\n" + "=" * 60)
    print("Demo complete! Check out these features:")
    print("• Colorized unit movements and attacks")
    print("• Real-time battlefield display")
    print("• Turn-by-turn action logging") 
    print("• Unit health tracking")
    print("• Replay saved to demo_replay.json")
    
    if enable_web:
        print(f"• Web interface at http://localhost:{web_port}")
        print("  (Keep this script running to view the web interface)")
        print("\nPress Ctrl+C to exit...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
    
    visualizer.display_game_end("BlueCrabs", "BayBirds unit eliminated (demo scenario)")
    visualizer.cleanup()


def main():
    """Main entry point for the demo."""
    parser = argparse.ArgumentParser(description="Harford County Clash Visualization Demo")
    parser.add_argument("--web", action="store_true", help="Enable web interface")
    parser.add_argument("--web-port", type=int, default=8080, help="Web interface port")
    
    args = parser.parse_args()
    
    try:
        run_demo(enable_web=args.web, web_port=args.web_port)
    except KeyboardInterrupt:
        print("\nDemo interrupted by user.")
    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()