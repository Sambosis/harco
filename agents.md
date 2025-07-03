Harford County Clash – Turn-Based LLM-vs-LLM Strategy Game

Expanded Description:
The program is a self-contained, turn-based strategy simulation in which two large-language-model (LLM) “commanders” wage war for control of Harford County, Maryland.  
Key design decisions and rules:

1. Map & Geography  
   •  The game map is a fixed 10 × 10 grid that loosely overlays real Harford County geography.  
   •  Each cell is tagged with its closest real-world reference (e.g., “Bel Air”, “Aberdeen Proving Ground”, “Havre de Grace”, “Edgewood”, “Forest Hill”, “Jarrettsville”, etc.).  
   •  A JSON asset (assets/harford_map.json) stores: cell coordinates, terrain type (urban, rural, water, forest), and adjacency cost modifiers.

2. Factions  
   •  Team Chesapeake (starting base: Havre de Grace, top-right corner).  
   •  Team Susquehanna (starting base: Aberdeen, lower-right quadrant).  
   •  Each team state contains: troop_count, resource_stockpile, current_position(s), visibility_range, and a battle log visible only to that team.

3. Victory Conditions  
   •  Capture and occupy the enemy base OR have more total resources after 20 turns.

4. Turn Loop  
   1. Engine packages a structured JSON “intel report” for Team A (their private data + publicly observable map data).  
   2. Team A’s LLM is invoked with that intel and returns a JSON action (move, attack, recruit, gather).  
   3. Engine validates and executes Team A’s action.  
   4. Repeat steps 1-3 for Team B.  
   5. Resolve combat if units enter same cell.  
   6. Append turn summary to a public log (visible to the human observer) and to each team’s private log.  
   7. Check victory conditions; else advance to next turn.

5. Ensuring LLM Isolation  
   •  Each LLM call is made with only that faction’s intel; opponent’s private state is never included.  
   •  Separate prompt templates and conversation histories are maintained per team to prevent leakage.

6. Watching the Game  
   •  A real-time textual viewer prints to stdout after each turn: the public map with unit positions, turn number, and a concise summary of both sides’ publicly visible actions.  
   •  Optional command-line flag ­--replay saves the public log to disk for later review.

7. Technology Choices  
   •  Python ≥ 3.10.  
   •  OpenAI ChatCompletion API by default; alternate provider can be set with ENV vars (e.g., OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.).  
   •  No external UI libraries—stdout printing keeps dependencies minimal.  
   •  Hermetic, single-process simulation; deterministic random seed can be supplied for reproducible replays.

8. Configuration  
   •  All tunables (turn limit, starting troops, resource spawn rates, random seed) live in src/config.py.  
   •  LLM model names and temperature pulled from env or default constants.

File Tree:
- project_root/
  - src/
    - __init__.py  
      Purpose: Marks ‘src’ as a package.  
      Import: `import src`
    - main.py  
      Purpose: CLI entry point. Parses args, seeds RNG, instantiates GameEngine, starts turn loop, triggers Viewer.  
      Import: `from src import main`
    - config.py  
      Purpose: Centralized game constants and environment variable helpers.  
      Import: `from src import config`
    - map_data.py  
      Purpose: Loads and provides utility access to assets/harford_map.json.  
      Import: `from src import map_data`
    - team_state.py  
      Purpose: Dataclass encapsulating all mutable state for a faction.  
      Import: `from src import team_state`
    - llm_player.py  
      Purpose: Wrapper around OpenAI (or other) chat API; handles prompt creation, isolation, rate limiting, and JSON action validation.  
      Import: `from src import llm_player`
    - game_engine.py  
      Purpose: Core rules engine—executes turns, validates actions, resolves combat/resources, updates states, checks victory.  
      Import: `from src import game_engine`
    - viewer.py  
      Purpose: Formats and prints public game state after each turn; handles optional replay logging.  
      Import: `from src import viewer`
    - utils.py  
      Purpose: Miscellaneous helpers (e.g., randomness, JSON schema validation, colored terminal output).  
      Import: `from src import utils`
  - assets/
    - harford_map.json  
      Purpose: Grid definition with cell-to-location metadata and terrain modifiers, consumed by map_data.py.