# 🎮 Harford County Clash - Visual Display System

The Harford County Clash now includes an enhanced visual display system that brings the battles to life with real-time animations, colorized terminal output, and an optional web interface!

## ✨ Features

### 🖥️ Enhanced Terminal Display
- **Colorized battlefield grid** with terrain types (water 🌊, urban 🏙, forest 🌲, rural 🏞)
- **Real-time unit tracking** with team-colored units (🦀 BlueCrabs in blue, 🦅 BayBirds in red)
- **Animated action display** showing movements with arrows ➡️ and attacks with ⚔️
- **Unit health visualization** with color-coded HP indicators
- **Turn-by-turn summaries** with casualty reports and action statistics
- **Headquarters highlighting** with special 🏰 symbols

### 🌐 Web Interface (Optional)
- **Interactive battlefield grid** with hover tooltips showing unit details
- **Real-time game state updates** via automatic polling
- **Team status panels** showing unit counts and health
- **Event log** tracking all actions and their outcomes
- **Responsive design** that works on desktop and mobile

### 📁 Replay System
- **Automatic replay saving** to JSON files with complete game history
- **Turn-by-turn action logging** including success/failure status
- **Unit state tracking** before and after each turn
- **Detailed event metadata** for post-game analysis

## 🚀 Quick Start

### Basic Game with Enhanced Visuals
```bash
python -m harford_strategy_game.main
```
The enhanced terminal display is enabled by default!

### With Web Interface
```bash
python -m harford_strategy_game.main --web
```
Then open http://localhost:8080 in your browser to see the live web interface.

### Demo Mode
Try the standalone visualization demo:
```bash
python harford_strategy_game/demo_visualization.py
```

Or with web interface:
```bash
python harford_strategy_game/demo_visualization.py --web
```

## 🎛️ Command Line Options

### Visualization Options
- `--no-visual` - Disable enhanced display (use basic text output)
- `--web` - Enable web-based visualization interface
- `--web-port PORT` - Set web interface port (default: 8080)

### Existing Options
- `--turns N` - Set maximum number of turns
- `--seed N` - Set random seed for reproducible games
- `--model MODEL` - Choose LLM model (e.g., gpt-4)
- `--temperature T` - Set AI creativity level (0.0-1.0)
- `--replay FILE` - Save replay to custom file location

### Example Commands
```bash
# Basic game with enhanced visuals
python -m harford_strategy_game.main

# Web interface on custom port
python -m harford_strategy_game.main --web --web-port 9000

# Tournament mode with replay saving
python -m harford_strategy_game.main --turns 100 --seed 42 --replay tournament_game1.json

# Classic text-only mode
python -m harford_strategy_game.main --no-visual

# Full featured battle with web interface
python -m harford_strategy_game.main --web --turns 75 --model gpt-4 --temperature 0.6
```

## 🎭 What You'll See

### Terminal Display
```
🦀🦀🦀🦀🦀🦀🦀🦀🦀🦀⚔️🦅🦅🦅🦅🦅🦅🦅🦅🦅🦅
HARFORD COUNTY CLASH - VISUAL DISPLAY
🦀🦀🦀🦀🦀🦀🦀🦀🦀🦀⚔️🦅🦅🦅🦅🦅🦅🦅🦅🦅🦅

🦀 BlueCrabs - 3 units
   HQ: 4,5

🦅 BayBirds - 3 units  
   HQ: 8,2

📍 INITIAL BATTLEFIELD
------------------------------------------------------------
     0  1  2  3  4  5  6  7  8  9
 0 🌊 🌲 🌲 🌊 🌲 🌲 🌊 🌲 🌲 🌊  0
 1 🌲 🏞 🏞 🏞 🏞 🏞 🏞 🏞 🦀 🌲  1
 2 🌲 🏞 🏞 🏞 🏞 🏞 🏞 🏞 🏰 🌲  2
 3 🌊 🏞 🏞 🏙 🏞 🏞 🏙 🏞 🦅 🌊  3
 4 🌲 🏞 🏞 🏞 🏞 🏞 🏞 🏞 🏞 🌲  4
 5 🌲 🏞 🦀 🏞 🏰 🏞 🏞 🏞 🏞 🌲  5
 6 🌊 🏞 🏞 🏙 🏞 🏞 🏙 🏞 🏞 🌊  6
 7 🌲 🏞 🏞 🏞 🏞 🏞 🏞 🦅 🏞 🌲  7
 8 🌲 🦀 🏞 🏞 🏞 🏞 🏞 🦅 🏞 🌲  8
 9 🌊 🌲 🌲 🌊 🌲 🌲 🌊 🌲 🌲 🌊  9
     0  1  2  3  4  5  6  7  8  9

============================================================
🎮 TURN 1
============================================================
  🦀 BlueCrabs-1 ➡️ moves (2,5) → (3,5)
  🦀 BlueCrabs-2 ➡️ moves (1,8) → (2,8)
  🦅 BayBirds-1 ⚔️ attacks BlueCrabs-1 for 5 damage!
  🦅 BayBirds-2 ➡️ moves (7,8) → (6,8)

📋 TURN 1 SUMMARY
----------------------------------------
📊 Actions: 3 moves, 1 attacks
⚔️ Total damage dealt: 5
```

### Action Types You'll See
- **➡️ Moves** - Unit movement with source → target coordinates
- **⚔️ Attacks** - Combat actions with damage amounts
- **⏸️ Pass** - Units that take no action
- **❌ Failed** - Blocked moves or invalid attacks
- **💀 Casualties** - Units eliminated during the turn

### Web Interface Features
- **Live battlefield** updates every 2 seconds
- **Unit tooltips** showing ID and health when hovering
- **Color-coded terrain** matching the terminal display
- **Team status** showing current unit counts
- **Event log** with recent actions
- **HQ highlighting** with golden borders

## 🛠️ Technical Details

### Replay File Format
The replay system saves games as JSON files with this structure:
```json
{
  "game_info": {
    "timestamp": 1640995200.0,
    "current_turn": 15
  },
  "turns": [
    {
      "turn": 1,
      "timestamp": 1640995201.0,
      "events": [
        {
          "unit_id": "BlueCrabs-1",
          "team_id": "BlueCrabs",
          "action": "move",
          "source": {"x": 2, "y": 5},
          "target": {"x": 3, "y": 5},
          "success": true
        }
      ],
      "unit_states": {
        "BlueCrabs-1": {
          "coord": {"x": 3, "y": 5},
          "hp": 10,
          "alive": true
        }
      }
    }
  ]
}
```

### Performance Notes
- Terminal display adds minimal overhead
- Web interface uses polling (2-second intervals)
- Replay files grow ~1KB per turn
- Color support auto-detected (disable with `HCC_NO_COLOR=1`)

## 🎨 Customization

### Disable Colors
```bash
export HCC_NO_COLOR=1
python -m harford_strategy_game.main
```

### Custom Web Port
```bash
python -m harford_strategy_game.main --web --web-port 3000
```

### Save Replays to Custom Location
```bash
python -m harford_strategy_game.main --replay "battles/epic_game_$(date +%Y%m%d).json"
```

## 🔧 Troubleshooting

### Web Interface Won't Start
- Check if port is already in use: `netstat -an | grep :8080`
- Try a different port: `--web-port 8081`
- Check firewall settings

### Colors Not Working
- Ensure terminal supports ANSI colors
- Check `HCC_NO_COLOR` environment variable
- Try a different terminal emulator

### Performance Issues
- Use `--no-visual` for faster execution
- Disable web interface if not needed
- Consider shorter turn limits for testing

## 🎯 Tips for Best Experience

1. **Terminal Size**: Use at least 80x30 terminal for best display
2. **Browser**: Modern browsers work best for web interface
3. **Monitoring**: Watch both terminal and web interface simultaneously
4. **Replays**: Save important games for later analysis
5. **Demo**: Run the demo first to see all features

## 🔮 Future Enhancements

Planned features for future releases:
- Animation between turns with smooth transitions
- Sound effects for attacks and movements  
- Replay viewer with step-through controls
- Tournament bracket visualization
- Unit trail tracking showing movement history
- 3D battlefield rendering option
- Real-time spectator mode for multiple viewers

---

*Ready to watch AI battle in style? The battlefield awaits!* ⚔️