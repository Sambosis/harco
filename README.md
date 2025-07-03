# Harford County Clash 🦀⚔️🦅

A turn-based LLM vs LLM strategy game set in the historic landmarks of Harford County, Maryland.

## 🎯 Game Overview

**Harford County Clash** is an AI-powered strategy game where two language model agents battle for territorial dominance across a 10×10 grid representing real locations in Harford County, MD. Each faction commands military units in tactical warfare featuring movement, combat, and strategic objectives.

### 🏟️ The Battlefield

The game takes place on a 10×10 grid featuring authentic Harford County landmarks including:
- **Bel Air** (BlueCrabs headquarters)
- **Havre de Grace** (BayBirds headquarters) 
- **Aberdeen Proving Ground**
- **Fallston, Edgewood, Joppatowne** and many more

Different terrain types affect gameplay:
- **Rural** - Standard movement and combat
- **Urban** - Standard movement and combat  
- **Water** - Impassable terrain

## ⚔️ Factions

### 🦀 BlueCrabs
- **Headquarters:** Bel Air
- **Color:** Blue
- **Starting Position:** Center-left of the map

### 🦅 BayBirds  
- **Headquarters:** Havre de Grace
- **Color:** Red
- **Starting Position:** Upper-right of the map

## 🎮 Game Mechanics

### Units
- Each team starts with **3 units**
- **Health Points:** 10 HP per unit
- **Attack Power:** 5 damage per attack
- **Visibility:** 2-tile radius (fog of war)

### Actions
Each turn, units can perform one of the following actions:

1. **Move** - Move one tile in cardinal directions (N, S, E, W)
   - Cannot move through water or occupied tiles
   - Movement conflicts (multiple units targeting same tile) result in no movement

2. **Attack** - Attack an adjacent enemy unit
   - Must be within 1 tile (orthogonally adjacent)
   - Deals 5 damage
   - All attacks resolve simultaneously

3. **Pass** - Take no action this turn

### Turn Structure
1. **Alternating Priority:** Teams alternate who moves first each turn
2. **Simultaneous Resolution:** All actions resolve at the same time
3. **Movement Phase:** All movement happens first
4. **Combat Phase:** All attacks resolve simultaneously

### Fog of War
- Units can only see enemies within a 2-tile radius
- Your own units are always visible
- The map terrain is fully known
- Enemy headquarters are always visible

## 🏆 Victory Conditions

A team wins by achieving either:

1. **Headquarters Capture** - Move a unit onto the enemy headquarters
2. **Total Elimination** - Destroy all enemy units

If neither condition is met after 50 turns, the game ends in a draw.

## 🚀 Installation & Setup

### Prerequisites
- Python 3.8+
- OpenAI API access (or compatible LLM API)

### Installation
```bash
# Clone the repository
git clone <repository-url>
cd harford_strategy_game

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
export OPENAI_API_KEY="your-api-key-here"
```

### Environment Variables
Create a `.env` file or export these variables:
```bash
OPENAI_API_KEY=your-openai-api-key
HCC_LOG_LEVEL=INFO  # Optional: DEBUG, INFO, WARNING, ERROR
```

## 🎯 Usage

### Basic Game
```bash
python -m harford_strategy_game.main
```

### Advanced Options
```bash
# Custom turn limit
python -m harford_strategy_game.main --turns 100

# Deterministic replay with seed
python -m harford_strategy_game.main --seed 12345

# Different AI model
python -m harford_strategy_game.main --model gpt-4

# Adjust AI creativity
python -m harford_strategy_game.main --temperature 0.3

# Save replay log
python -m harford_strategy_game.main --replay game_replay.json

# Combine options
python -m harford_strategy_game.main --turns 75 --seed 42 --model gpt-4 --temperature 0.5
```

### Command Line Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--turns` | int | 50 | Maximum number of turns |
| `--seed` | int | None | Random seed for deterministic games |
| `--model` | str | gpt-4.1-nano | LLM model name |
| `--temperature` | float | 0.8 | AI creativity (0.0-1.0) |
| `--replay` | str | None | File path to save JSON replay log |

## 🔧 Development

### Project Structure
```
harford_strategy_game/
├── main.py          # CLI entry point and orchestration
├── game_state.py    # Core game mechanics and state management
├── referee.py       # Turn management and rule enforcement  
├── llm_agent.py     # AI agent implementation
├── local_map.py     # Map generation and landmark data
└── utils.py         # Utility functions and helpers
```

### Key Classes
- **GameState** - Manages units, tiles, and game rules
- **Referee** - Controls turn flow and victory conditions
- **LLMAgent** - AI-powered faction commander
- **MapFactory** - Generates the Harford County battlefield

### Adding Custom Maps
Modify `local_map.py` to create new battlefields:
1. Update `LANDMARK_GRID` with your location names
2. Adjust `BLUECRABS_HQ` and `BAYBIRDS_HQ` coordinates
3. Customize terrain types in `_infer_terrain_from_landmark()`

### Logging
Enable debug logging for detailed game analysis:
```bash
export HCC_LOG_LEVEL=DEBUG
python -m harford_strategy_game.main
```

## 🎮 Gameplay Tips

### For AI Agents
The game provides agents with:
- JSON battlefield state each turn
- Fog of war limitations
- Unit positions and health
- Available actions per unit

### Strategic Considerations
- **Early Game:** Secure defensive positions around your HQ
- **Mid Game:** Scout enemy positions and control key terrain
- **Late Game:** Push for HQ capture or eliminate remaining enemies
- **Positioning:** Use terrain and unit coordination effectively
- **Resource Management:** Preserve unit health while dealing damage

## 📊 Replay Analysis

Games can be saved as JSON replay files for analysis:
```bash
python -m harford_strategy_game.main --replay my_game.json
```

The replay contains:
- Complete turn-by-turn game state
- All unit actions and movements  
- Agent decision timings
- Final victory conditions

## 🤝 Contributing

We welcome contributions! Areas for improvement:
- New terrain types and effects
- Additional unit types and abilities
- Enhanced AI agent strategies
- Visualization and replay tools
- Performance optimizations

## 📜 License

[License information to be added]

## 🏛️ About Harford County

This game celebrates the rich history and geography of Harford County, Maryland. From the colonial port of Havre de Grace to the county seat of Bel Air, each landmark represents a real place with its own unique character and history.

---

*Ready to clash? May the best algorithm win!* 🏆