"""
visualizer.py

Real-time visual display system for Harford County Clash.

Provides multiple visualization modes:
- Enhanced terminal display with colors and animations
- Web-based interface with interactive grid
- Turn-by-turn action replays
- Battle statistics and unit tracking

Author
------
Harford County Clash visualization team
"""

from __future__ import annotations

import html
import json
import os
import time
import webbrowser
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple
from pathlib import Path
import threading
import http.server
import socketserver

from game_state import GameState, Unit, Coord
from utils import ANSIColor, colorize


@dataclass
class ActionEvent:
    """Represents a single action taken during a turn."""
    turn: int
    unit_id: str
    team_id: str
    action_type: str  # "move", "attack", "pass"
    source_coord: Coord
    target_coord: Optional[Coord] = None
    target_unit_id: Optional[str] = None
    damage_dealt: int = 0
    success: bool = True


@dataclass
class TurnSummary:
    """Summary of all events that occurred during a turn."""
    turn_number: int
    events: List[ActionEvent]
    unit_states_before: Dict[str, Dict[str, Any]]
    unit_states_after: Dict[str, Dict[str, Any]]
    timestamp: float


class GameVisualizer:
    """
    Main visualization controller that manages different display modes.
    """
    
    def __init__(self, 
                 enable_terminal_display: bool = True,
                 enable_web_interface: bool = False,
                 web_port: int = 8080,
                 save_replay: bool = True,
                 replay_file: str = "game_replay.json"):
        self.enable_terminal = enable_terminal_display
        self.enable_web = enable_web_interface
        self.web_port = web_port
        self.save_replay = save_replay
        self.replay_file = replay_file
        
        # Game state tracking
        self.current_game_state: Optional[GameState] = None
        self.previous_game_state: Optional[GameState] = None
        self.turn_summaries: List[TurnSummary] = []
        self.current_events: List[ActionEvent] = []
        
        # Web interface setup
        self.web_server = None
        self.web_thread = None
        
        if self.enable_web:
            self._setup_web_interface()
    
    def initialize_game(self, initial_state: GameState) -> None:
        """Initialize the visualizer with the starting game state."""
        self.current_game_state = initial_state
        self.previous_game_state = None
        self.turn_summaries = []
        self.current_events = []
        
        if self.enable_terminal:
            self._print_game_header()
            self._display_initial_map()
        
        if self.enable_web:
            self._update_web_display()
    
    def begin_turn(self, turn_number: int) -> None:
        """Start tracking events for a new turn."""
        self.current_events = []
        
        if self.enable_terminal:
            print(f"\n{'='*60}")
            print(f"🎮 TURN {turn_number}")
            print(f"{'='*60}")
    
    def record_action(self, 
                     unit_id: str, 
                     action_type: str, 
                     source_coord: Coord,
                     target_coord: Optional[Coord] = None,
                     target_unit_id: Optional[str] = None,
                     damage_dealt: int = 0,
                     success: bool = True) -> None:
        """Record an action event for the current turn."""
        if not self.current_game_state:
            return
            
        unit = self.current_game_state.units.get(unit_id)
        if not unit:
            return
            
        event = ActionEvent(
            turn=self.current_game_state.turn_counter + 1,
            unit_id=unit_id,
            team_id=unit.team_id,
            action_type=action_type,
            source_coord=source_coord,
            target_coord=target_coord,
            target_unit_id=target_unit_id,
            damage_dealt=damage_dealt,
            success=success
        )
        
        self.current_events.append(event)
        
        if self.enable_terminal:
            self._display_action_event(event)
    
    def end_turn(self, new_game_state: GameState) -> None:
        """Complete the current turn and update the display."""
        if not self.current_game_state:
            return
            
        # Capture unit states before and after
        unit_states_before = {
            uid: {
                'coord': {'x': unit.coord.x, 'y': unit.coord.y},
                'hp': unit.hp,
                'alive': unit.is_alive()
            }
            for uid, unit in self.current_game_state.units.items()
        }
        
        unit_states_after = {
            uid: {
                'coord': {'x': unit.coord.x, 'y': unit.coord.y},
                'hp': unit.hp,
                'alive': unit.is_alive()
            }
            for uid, unit in new_game_state.units.items()
        }
        
        # Create turn summary
        turn_summary = TurnSummary(
            turn_number=new_game_state.turn_counter,
            events=self.current_events.copy(),
            unit_states_before=unit_states_before,
            unit_states_after=unit_states_after,
            timestamp=time.time()
        )
        
        self.turn_summaries.append(turn_summary)
        
        # Update states
        self.previous_game_state = self.current_game_state
        self.current_game_state = new_game_state
        
        if self.enable_terminal:
            self._display_turn_results(turn_summary)
            self._display_current_map()
        
        if self.enable_web:
            self._update_web_display()
        
        if self.save_replay:
            self._save_replay_data()
    
    def display_game_end(self, winner: Optional[str], reason: str) -> None:
        """Display the final game results."""
        if self.enable_terminal:
            self._display_game_end_terminal(winner, reason)
        
        if self.enable_web:
            self._update_web_display_final(winner, reason)
        
        if self.save_replay:
            self._save_final_replay()
    
    def _print_game_header(self) -> None:
        """Print the initial game setup information."""
        print("\n" + "🦀" * 30 + "⚔️" + "🦅" * 30)
        print(colorize("HARFORD COUNTY CLASH - VISUAL DISPLAY", ANSIColor.YELLOW, bold=True))
        print("🦀" * 30 + "⚔️" + "🦅" * 30)
        print()
        
        if self.current_game_state:
            # Display team information
            blue_units = [u for u in self.current_game_state.units.values() if u.team_id == "BlueCrabs"]
            red_units = [u for u in self.current_game_state.units.values() if u.team_id == "BayBirds"]
            
            print(f"🦀 {colorize('BlueCrabs', ANSIColor.BLUE, bold=True)} - {len(blue_units)} units")
            print(f"   HQ: {self.current_game_state.team_hqs['BlueCrabs'].x},{self.current_game_state.team_hqs['BlueCrabs'].y}")
            
            print(f"🦅 {colorize('BayBirds', ANSIColor.RED, bold=True)} - {len(red_units)} units")
            print(f"   HQ: {self.current_game_state.team_hqs['BayBirds'].x},{self.current_game_state.team_hqs['BayBirds'].y}")
            print()
    
    def _display_initial_map(self) -> None:
        """Display the initial map with unit positions."""
        if not self.current_game_state:
            return
            
        print("📍 INITIAL BATTLEFIELD")
        print("-" * 60)
        self._print_map_grid()
        print()
    
    def _display_current_map(self) -> None:
        """Display the current map state."""
        if not self.current_game_state:
            return
            
        print("\n📍 CURRENT BATTLEFIELD")
        print("-" * 60)
        self._print_map_grid()
        self._print_unit_status()
        print()
    
    def _print_map_grid(self) -> None:
        """Print the game grid with units and terrain."""
        if not self.current_game_state:
            return
            
        # Column headers
        print("   ", end="")
        for x in range(10):
            print(f" {x:2}", end="")
        print()
        
        # Rows
        for y in range(10):
            print(f"{y:2} ", end="")
            
            for x in range(10):
                coord = Coord(x, y)
                
                # Find unit at this position
                unit_at_pos = None
                for unit in self.current_game_state.units.values():
                    if unit.coord == coord and unit.is_alive():
                        unit_at_pos = unit
                        break
                
                # Find tile info
                tile = next((t for t in self.current_game_state.tiles if t.coord == coord), None)
                
                # Check if this is an HQ
                is_hq = coord in self.current_game_state.team_hqs.values()
                
                if unit_at_pos:
                    # Display unit
                    if unit_at_pos.team_id == "BlueCrabs":
                        symbol = colorize("🦀", ANSIColor.BLUE, bold=True)
                    else:
                        symbol = colorize("🦅", ANSIColor.RED, bold=True)
                elif is_hq:
                    # Display HQ
                    if coord == self.current_game_state.team_hqs.get("BlueCrabs"):
                        symbol = colorize("🏰", ANSIColor.BLUE)
                    else:
                        symbol = colorize("🏰", ANSIColor.RED)
                else:
                    # Display terrain
                    if tile:
                        if tile.terrain_type == "water":
                            symbol = colorize("🌊", ANSIColor.CYAN)
                        elif tile.terrain_type == "urban":
                            symbol = colorize("🏙", ANSIColor.YELLOW)
                        elif tile.terrain_type == "forest":
                            symbol = colorize("🌲", ANSIColor.GREEN)
                        else:
                            symbol = "🏞"
                    else:
                        symbol = "  "
                
                print(f"{symbol:3}", end="")
            
            print(f" {y}")
        
        # Legend
        print("\nLegend:")
        print(f"🦀 {colorize('BlueCrabs units', ANSIColor.BLUE)}")
        print(f"🦅 {colorize('BayBirds units', ANSIColor.RED)}")
        print(f"🏰 Headquarters")
        print(f"🌊 Water  🏙 Urban  🌲 Forest  🏞 Rural")
    
    def _print_unit_status(self) -> None:
        """Print detailed unit status information."""
        if not self.current_game_state:
            return
            
        print("\n📊 UNIT STATUS")
        print("-" * 60)
        
        for team_id in ["BlueCrabs", "BayBirds"]:
            team_units = [u for u in self.current_game_state.units.values() 
                         if u.team_id == team_id and u.is_alive()]
            
            color = ANSIColor.BLUE if team_id == "BlueCrabs" else ANSIColor.RED
            icon = "🦀" if team_id == "BlueCrabs" else "🦅"
            
            print(f"\n{icon} {colorize(team_id, color, bold=True)}")
            
            if not team_units:
                print(f"  {colorize('NO SURVIVING UNITS', ANSIColor.RED)}")
                continue
                
            for unit in sorted(team_units, key=lambda u: u.id):
                hp_color = ANSIColor.GREEN if unit.hp > 7 else ANSIColor.YELLOW if unit.hp > 3 else ANSIColor.RED
                print(f"  {unit.id}: ({unit.coord.x},{unit.coord.y}) HP:{colorize(str(unit.hp), hp_color)}/10")
    
    def _display_action_event(self, event: ActionEvent) -> None:
        """Display a single action event with visual formatting."""
        team_color = ANSIColor.BLUE if event.team_id == "BlueCrabs" else ANSIColor.RED
        team_icon = "🦀" if event.team_id == "BlueCrabs" else "🦅"
        
        if event.action_type == "move":
            if event.success and event.target_coord:
                arrow = "➡️"
                message = f"{team_icon} {colorize(event.unit_id, team_color)} {arrow} moves ({event.source_coord.x},{event.source_coord.y}) → ({event.target_coord.x},{event.target_coord.y})"
            else:
                message = f"{team_icon} {colorize(event.unit_id, team_color)} ❌ move blocked from ({event.source_coord.x},{event.source_coord.y})"
        
        elif event.action_type == "attack":
            if event.success and event.damage_dealt > 0:
                message = f"{team_icon} {colorize(event.unit_id, team_color)} ⚔️ attacks {event.target_unit_id} for {colorize(str(event.damage_dealt), ANSIColor.RED)} damage!"
            else:
                message = f"{team_icon} {colorize(event.unit_id, team_color)} ❌ attack failed"
        
        elif event.action_type == "pass":
            message = f"{team_icon} {colorize(event.unit_id, team_color)} ⏸️ passes turn"
        
        else:
            message = f"{team_icon} {colorize(event.unit_id, team_color)} {event.action_type}"
        
        print(f"  {message}")
    
    def _display_turn_results(self, turn_summary: TurnSummary) -> None:
        """Display the results of the completed turn."""
        print(f"\n📋 TURN {turn_summary.turn_number} SUMMARY")
        print("-" * 40)
        
        # Count casualties
        casualties = []
        for uid, unit_after in turn_summary.unit_states_after.items():
            unit_before = turn_summary.unit_states_before.get(uid)
            if unit_before and unit_before['alive'] and not unit_after['alive']:
                casualties.append(uid)
        
        if casualties:
            print(f"💀 Casualties: {', '.join(casualties)}")
        
        # Movement summary
        movements = [e for e in turn_summary.events if e.action_type == "move" and e.success]
        attacks = [e for e in turn_summary.events if e.action_type == "attack" and e.success]
        
        print(f"📊 Actions: {len(movements)} moves, {len(attacks)} attacks")
        
        if attacks:
            total_damage = sum(e.damage_dealt for e in attacks)
            print(f"⚔️ Total damage dealt: {total_damage}")
    
    def _display_game_end_terminal(self, winner: Optional[str], reason: str) -> None:
        """Display game end results in terminal."""
        print("\n" + "🏆" * 20)
        print(colorize("GAME OVER", ANSIColor.YELLOW, bold=True))
        print("🏆" * 20)
        
        if winner:
            color = ANSIColor.BLUE if winner == "BlueCrabs" else ANSIColor.RED
            icon = "🦀" if winner == "BlueCrabs" else "🦅"
            print(f"\n🎉 WINNER: {icon} {colorize(winner, color, bold=True)}")
        else:
            print(f"\n🤝 {colorize('DRAW', ANSIColor.YELLOW, bold=True)}")
        
        print(f"Reason: {reason}")
        print(f"Total turns: {len(self.turn_summaries)}")
        
        # Final statistics
        print(f"\n📊 FINAL STATISTICS")
        print("-" * 30)
        
        for team_id in ["BlueCrabs", "BayBirds"]:
            survivors = [u for u in self.current_game_state.units.values() 
                        if u.team_id == team_id and u.is_alive()] if self.current_game_state else []
            
            color = ANSIColor.BLUE if team_id == "BlueCrabs" else ANSIColor.RED
            icon = "🦀" if team_id == "BlueCrabs" else "🦅"
            
            print(f"{icon} {colorize(team_id, color)}: {len(survivors)} survivors")
    
    def _setup_web_interface(self) -> None:
        """Set up the web interface server."""
        try:
            # Create web assets directory
            web_dir = Path("web_interface")
            web_dir.mkdir(exist_ok=True)
            
            # Create HTML template
            self._create_web_template(web_dir)
            
            # Start web server in a separate thread
            self._start_web_server(web_dir)
            
        except Exception as e:
            print(f"Warning: Could not start web interface: {e}")
            self.enable_web = False
    
    def _create_web_template(self, web_dir: Path) -> None:
        """Create the HTML template for the web interface."""
        html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Harford County Clash - Live Visualization</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #1a1a1a; color: white; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .grid { display: grid; grid-template-columns: repeat(10, 40px); gap: 2px; margin: 20px 0; }
        .cell { width: 40px; height: 40px; border: 1px solid #666; display: flex; align-items: center; justify-content: center; font-size: 18px; }
        .water { background-color: #4A90E2; }
        .urban { background-color: #F5A623; }
        .forest { background-color: #7ED321; }
        .rural { background-color: #8E8E93; }
        .bluecrabs { background-color: #0066cc !important; }
        .baybirds { background-color: #cc0000 !important; }
        .hq { border: 3px solid gold; }
        .sidebar { float: right; width: 300px; margin-left: 20px; }
        .main-content { margin-right: 320px; }
        .status-panel { background: #2a2a2a; padding: 15px; margin-bottom: 20px; border-radius: 5px; }
        .event-log { background: #2a2a2a; padding: 15px; border-radius: 5px; height: 400px; overflow-y: auto; }
        .event { margin-bottom: 10px; padding: 5px; border-left: 3px solid #666; padding-left: 10px; }
        .move { border-left-color: #4A90E2; }
        .attack { border-left-color: #E74C3C; }
        .pass { border-left-color: #95A5A6; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🦀⚔️🦅 Harford County Clash</h1>
            <div id="turn-info">Turn: 0</div>
        </div>
        
        <div class="sidebar">
            <div class="status-panel">
                <h3>Team Status</h3>
                <div id="team-status"></div>
            </div>
            
            <div class="event-log">
                <h3>Event Log</h3>
                <div id="events"></div>
            </div>
        </div>
        
        <div class="main-content">
            <div id="game-grid" class="grid"></div>
            <div id="legend">
                <h3>Legend</h3>
                <p>🦀 BlueCrabs | 🦅 BayBirds | 🏰 HQ</p>
                <p>🌊 Water | 🏙 Urban | 🌲 Forest | 🏞 Rural</p>
            </div>
        </div>
    </div>
    
    <script>
        function updateDisplay() {
            fetch('/game_state')
                .then(response => response.json())
                .then(data => {
                    updateGrid(data);
                    updateStatus(data);
                    updateEvents(data);
                })
                .catch(error => console.error('Error:', error));
        }
        
        function updateGrid(data) {
            const grid = document.getElementById('game-grid');
            grid.innerHTML = '';
            
            for (let y = 0; y < 10; y++) {
                for (let x = 0; x < 10; x++) {
                    const cell = document.createElement('div');
                    cell.className = 'cell';
                    
                    // Add terrain class
                    const terrain = data.tiles && data.tiles.find(t => t.coord.x === x && t.coord.y === y);
                    if (terrain) {
                        cell.classList.add(terrain.terrain_type);
                    }
                    
                    // Check for units
                    const unit = data.units && data.units.find(u => u.coord.x === x && u.coord.y === y);
                    if (unit) {
                        cell.textContent = unit.team_id === 'BlueCrabs' ? '🦀' : '🦅';
                        cell.classList.add(unit.team_id.toLowerCase());
                        cell.title = `${unit.id} (HP: ${unit.hp})`;
                    }
                    
                    // Check for HQ
                    if (data.hq) {
                        if ((data.hq.own.x === x && data.hq.own.y === y) || 
                            (data.hq.enemy.x === x && data.hq.enemy.y === y)) {
                            cell.classList.add('hq');
                            if (!unit) cell.textContent = '🏰';
                        }
                    }
                    
                    grid.appendChild(cell);
                }
            }
        }
        
        function updateStatus(data) {
            const statusDiv = document.getElementById('team-status');
            const turnDiv = document.getElementById('turn-info');
            
            turnDiv.textContent = `Turn: ${data.turn || 0}`;
            
            const blueUnits = data.units ? data.units.filter(u => u.team_id === 'BlueCrabs') : [];
            const redUnits = data.units ? data.units.filter(u => u.team_id === 'BayBirds') : [];
            
            statusDiv.innerHTML = `
                <div>🦀 BlueCrabs: ${blueUnits.length} units</div>
                <div>🦅 BayBirds: ${redUnits.length} units</div>
            `;
        }
        
        function updateEvents(data) {
            // Events would be updated based on the action log
            // This is a simplified version
        }
        
        // Update every 2 seconds
        setInterval(updateDisplay, 2000);
        updateDisplay(); // Initial load
    </script>
</body>
</html>"""
        
        (web_dir / "index.html").write_text(html_content)
    
    def _start_web_server(self, web_dir: Path) -> None:
        """Start the web server for the interface."""
        class GameStateHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, visualizer=None, **kwargs):
                self.visualizer = visualizer
                super().__init__(*args, directory=str(web_dir), **kwargs)
            
            def do_GET(self):
                if self.path == '/game_state':
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    
                    if self.visualizer and self.visualizer.current_game_state:
                        # Send current game state as JSON
                        state_data = self.visualizer.current_game_state.serialize_public_view("BlueCrabs")
                        self.wfile.write(json.dumps(state_data).encode())
                    else:
                        self.wfile.write(b'{}')
                else:
                    super().do_GET()
        
        # Create handler with visualizer reference
        def handler_factory(*args, **kwargs):
            return GameStateHandler(*args, visualizer=self, **kwargs)
        
        try:
            with socketserver.TCPServer(("", self.web_port), handler_factory) as httpd:
                self.web_server = httpd
                self.web_thread = threading.Thread(
                    target=httpd.serve_forever, 
                    daemon=True
                )
                self.web_thread.start()
                
                print(f"🌐 Web interface available at: http://localhost:{self.web_port}")
                
        except Exception as e:
            print(f"Could not start web server: {e}")
            self.enable_web = False
    
    def _update_web_display(self) -> None:
        """Update the web display with current game state."""
        # The web interface polls the game state via HTTP
        # This method could trigger additional updates if needed
        pass
    
    def _update_web_display_final(self, winner: Optional[str], reason: str) -> None:
        """Update web display with final game results."""
        # Could add special handling for game end in web interface
        pass
    
    def _save_replay_data(self) -> None:
        """Save current replay data to file."""
        if not self.save_replay:
            return
            
        replay_data = {
            "game_info": {
                "timestamp": time.time(),
                "current_turn": len(self.turn_summaries)
            },
            "turns": []
        }
        
        for turn_summary in self.turn_summaries:
            turn_data = {
                "turn": turn_summary.turn_number,
                "timestamp": turn_summary.timestamp,
                "events": [
                    {
                        "unit_id": event.unit_id,
                        "team_id": event.team_id,
                        "action": event.action_type,
                        "source": {"x": event.source_coord.x, "y": event.source_coord.y},
                        "target": {"x": event.target_coord.x, "y": event.target_coord.y} if event.target_coord else None,
                        "target_unit": event.target_unit_id,
                        "damage": event.damage_dealt,
                        "success": event.success
                    }
                    for event in turn_summary.events
                ],
                "unit_states": turn_summary.unit_states_after
            }
            replay_data["turns"].append(turn_data)
        
        try:
            with open(self.replay_file, 'w') as f:
                json.dump(replay_data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save replay data: {e}")
    
    def _save_final_replay(self) -> None:
        """Save the final complete replay file."""
        self._save_replay_data()
        print(f"📁 Game replay saved to: {self.replay_file}")
    
    def cleanup(self) -> None:
        """Clean up resources (web server, files, etc.)."""
        if self.web_server:
            self.web_server.shutdown()
        if self.web_thread:
            self.web_thread.join(timeout=1)