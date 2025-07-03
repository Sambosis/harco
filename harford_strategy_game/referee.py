"""
referee.py

Central coordination engine responsible for enforcing rules, alternating
turns between LLM-controlled commanders, and producing all spectator-facing
stdout output.  The surrounding modules purposefully avoid *any* direct I/O
so they remain easy to unit-test; the referee therefore owns printing and
high-level flow-control.

Because many downstream classes are still skeletal at this stage of the
project, the implementation below focuses on *robust orchestration* rather
than deep game-rules logic.  Where full validation would normally occur, the
referee performs best-effort sanity checks and gracefully degrades to
no-op ("pass") behaviour if something looks fishy.  Heavy-weight rules
enforcement ultimately lives inside `GameState.apply_actions`.
"""

from __future__ import annotations

import copy
import json
import random
import sys
import time
from typing import Any, Dict, List, Mapping, Protocol

# Internal imports
# --------------------------------------------------------------------------- #
import game_state  # type: ignore  – concrete implementation supplied elsewhere
from visualizer import GameVisualizer

# --------------------------------------------------------------------------- #
# Constants & Helper Types                                                    #
# --------------------------------------------------------------------------- #

_VALID_ACTION_TYPES: set[str] = {"move", "attack", "recruit", "gather", "pass"}


class LLMAgent(Protocol):  # pragma: no cover – runtime duck-typed
    """
    Structural typing stub for an LLM-powered commander.

    The concrete implementation lives in ``llm_agent.py`` (or test doubles).
    Only the surface used by the referee is defined here.
    """

    # Human-readable name (e.g., "Team Chesapeake")
    name: str
    # Faction identifier used by `GameState` (e.g., "CHESAPEAKE")
    team_id: str

    # Conversations/history live entirely inside the agent object; the
    # referee never sees them.
    def decide(self, intel: Dict[str, Any]) -> Dict[str, Any]: ...  # noqa: D401,E501


# --------------------------------------------------------------------------- #
# Referee                                                                     #
# --------------------------------------------------------------------------- #


class Referee:
    """
    Orchestrates the turn-based simulation, ensuring rule compliance and
    fairness between the competing LLM agents.
    """

    # ------------------------------- Construction ------------------------ #

    def __init__(self, map_obj: Any, agents: List[LLMAgent], *, seed: int | None = None,
                 enable_visualization: bool = True,
                 enable_web_interface: bool = False,
                 web_port: int = 8080) -> None:
        """
        Parameters
        ----------
        map_obj
            A factory or data-holder that is capable of producing the initial
            :pyclass:`game_state.GameState` instance via a ``build_initial_state``
            method (see ``local_map.MapFactory``).
        agents
            Exactly two commanders – order is canonical but first-mover
            advantage alternates every turn.
        seed
            Deterministic RNG seed.  The referee itself uses randomness only
            for tie-break helpers (e.g., shuffling equal-priority actions).
        enable_visualization
            Whether to enable the enhanced visual display system.
        enable_web_interface
            Whether to start the web-based visualization interface.
        web_port
            Port for the web interface (default: 8080).
        """
        self._validate_agent_count(agents)
        self._agents: List[LLMAgent] = agents
        self._game_state: game_state.GameState = self._initialise_game_state(map_obj)
        self._rng: random.Random = random.Random(seed)
        self._turn_counter: int = 0
        self._start_wall_clock: float = time.time()
        
        # Initialize visualization system
        self._visualizer = GameVisualizer(
            enable_terminal_display=enable_visualization,
            enable_web_interface=enable_web_interface,
            web_port=web_port,
            save_replay=True,
            replay_file="harford_county_clash_replay.json"
        ) if enable_visualization else None
        
        if self._visualizer:
            self._visualizer.initialize_game(self._game_state)

    # ------------------------------- Public API ------------------------- #

    def run(self, max_turns: int = 50) -> None:
        """
        Execute the primary game loop until a win condition or hard turn limit.

        All spectator output occurs inside this method – one block per turn
        plus a final scoreboard.
        """
        if not self._visualizer:
            self._print_banner()

        while self._turn_counter < max_turns:
            self._turn_counter += 1
            
            if self._visualizer:
                self._visualizer.begin_turn(self._turn_counter)
            else:
                print(f"\n=== TURN {self._turn_counter} ===============================")

            # 1. Determine acting order (alternating first player every turn)
            order: List[int] = self._determine_turn_order()

            # 2. Collect & validate each agent's actions
            combined_actions: Dict[str, Dict[str, Any]] = {}
            validation_reports: List[str] = []  # gather log msgs for summary
            for agent_idx in order:
                actions, report = self._collect_agent_actions(agent_idx)
                combined_actions.update(actions)
                if report:
                    validation_reports.append(report)

            # 3. Apply simultaneous resolution inside GameState with visualization tracking
            previous_state = copy.deepcopy(self._game_state)
            self._apply_actions_and_resolve(combined_actions, previous_state)

            # 4. Spectator summary (state + validation issues + notable events)
            if self._visualizer:
                self._visualizer.end_turn(self._game_state)
            else:
                self._print_spectator_summary(validation_reports)

            # 5. Check victory
            if self._check_victory_conditions(max_turns):
                break

        # Game ended - display final results
        winner = self._determine_winner()
        reason = self._determine_win_reason(max_turns)
        
        if self._visualizer:
            self._visualizer.display_game_end(winner, reason)
        else:
            self._print_final_scoreboard()

    # --------------------------- Internal Helpers ------------------------ #

    # Game-state initialisation ------------------------------------------ #

    @staticmethod
    def _validate_agent_count(agents: List[LLMAgent]) -> None:
        if len(agents) != 2:
            raise ValueError("Referee requires exactly two LLMAgent instances.")

    def _initialise_game_state(self, map_obj: Any) -> game_state.GameState:
        """
        Delegate to the supplied map factory to build the canonical
        :pyclass:`game_state.GameState`.
        """
        if not hasattr(map_obj, "build_initial_state"):
            raise AttributeError(
                "Map object is missing required `build_initial_state` method."
            )
        initial_state = map_obj.build_initial_state()
        if not isinstance(initial_state, game_state.GameState):  # defensive
            raise TypeError("MapFactory.build_initial_state() returned unexpected type.")
        return initial_state

    # Turn-order helper --------------------------------------------------- #

    def _determine_turn_order(self) -> List[int]:
        """
        Alternate who moves first each turn while keeping ordering deterministic.
        Turn 1 -> agent[0] first, Turn 2 -> agent[1] first, etc.
        """
        if (self._turn_counter % 2) == 1:
            return [0, 1]
        return [1, 0]

    # Action collection / validation ------------------------------------- #

    def _collect_agent_actions(self, agent_idx: int) -> tuple[Dict[str, Dict[str, Any]], str]:
        """
        Returns (validated_action_dict, validation_report_message)
        The second item is empty string if all good, otherwise a short note
        to surface in the spectator summary.
        """
        agent: LLMAgent = self._agents[agent_idx]

        # 1. Build the perspective-limited intel report
        try:
            intel = self._game_state.serialize_public_view(agent.team_id)
        except Exception as exc:  # pragma: no cover – GameState failure
            # Catastrophic serialization error – agent gets no info and must pass
            print(
                f"[WARN] Failed serialising intel for agent '{agent.name}': {exc}",
                file=sys.stderr,
            )
            intel = {}

        # 2. Ask the agent for its intended orders
        try:
            raw_actions = agent.decide(copy.deepcopy(intel))
        except Exception as exc:
            print(f"[WARN] Agent '{agent.name}' raised during decide(): {exc}", file=sys.stderr)
            raw_actions = {}

        # 3. Validate basic schema & coerce illegal directives to "pass"
        validated: Dict[str, Dict[str, Any]] = {}
        illegal_entries: List[str] = []
        team_unit_ids = [u_id for u_id, u in self._game_state.units.items() if u.team_id == agent.team_id]

        if not isinstance(raw_actions, Mapping):
            illegal_entries.append("<non-mapping root object>")
            raw_actions = {}

        # iterate over every unit we *currently* control – missing entries -> implicit pass
        for unit_id in team_unit_ids:
            action = raw_actions.get(unit_id, {"action": "pass"})
            if self._is_valid_action(action):
                validated[unit_id] = action
            else:
                illegal_entries.append(unit_id)
                validated[unit_id] = {"action": "pass"}

        # also ignore any extraneous unit keys the LLM tried to command
        if illegal_entries:
            report = (
                f"Agent '{agent.name}' issued invalid orders for: {', '.join(illegal_entries)}"
            )
        else:
            report = ""
        return validated, report

    @staticmethod
    def _is_valid_action(action: Any) -> bool:
        """
        Very lightweight schema check: expects a dict with an "action" key whose
        value is one of the recognised strings.
        """
        if not isinstance(action, Mapping):
            return False
        kind = action.get("action")
        return isinstance(kind, str) and kind in _VALID_ACTION_TYPES

    # ------------------------ Apply / Resolve --------------------------- #

    def _apply_actions_and_resolve(self, combined_actions: Dict[str, Dict[str, Any]], 
                                 previous_state: game_state.GameState) -> None:
        """
        Hand the merged action dictionary to GameState for simultaneous
        resolution.  Exceptions inside GameState are fatal (they indicate
        a rules engine bug rather than agent misbehaviour).
        """
        # Track actions for visualization
        if self._visualizer:
            self._track_actions_for_visualization(combined_actions, previous_state)
        
        try:
            self._game_state.apply_actions(combined_actions)
        except Exception as exc:  # pragma: no cover
            print(f"[ERROR] GameState.apply_actions failed: {exc}", file=sys.stderr)
            raise

    def _track_actions_for_visualization(self, combined_actions: Dict[str, Dict[str, Any]], 
                                       previous_state: game_state.GameState) -> None:
        """Track individual actions for the visualizer."""
        if not self._visualizer:
            return
            
        for unit_id, action in combined_actions.items():
            unit = previous_state.units.get(unit_id)
            if not unit or not unit.is_alive():
                continue
                
            action_type = action.get("action", "pass").lower()
            source_coord = unit.coord
            
            if action_type == "move":
                direction = action.get("direction", "").upper()
                direction_deltas = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0)}
                delta = direction_deltas.get(direction)
                
                if delta:
                    target_coord = game_state.Coord(
                        source_coord.x + delta[0], 
                        source_coord.y + delta[1]
                    )
                    
                    # Check if move will succeed (simplified validation)
                    success = (0 <= target_coord.x < 10 and 0 <= target_coord.y < 10)
                    if success:
                        tile = next((t for t in previous_state.tiles if t.coord == target_coord), None)
                        success = tile is not None and tile.traversable
                    
                    self._visualizer.record_action(
                        unit_id=unit_id,
                        action_type="move",
                        source_coord=source_coord,
                        target_coord=target_coord,
                        success=success
                    )
                else:
                    self._visualizer.record_action(
                        unit_id=unit_id,
                        action_type="move",
                        source_coord=source_coord,
                        success=False
                    )
                    
            elif action_type == "attack":
                target_id = action.get("target_id", "")
                target_unit = previous_state.units.get(target_id)
                
                if target_unit and target_unit.is_alive():
                    # Calculate if attack will succeed
                    distance = abs(unit.coord.x - target_unit.coord.x) + abs(unit.coord.y - target_unit.coord.y)
                    success = (distance == 1 and target_unit.team_id != unit.team_id)
                    damage = unit.attack_power if success else 0
                    
                    self._visualizer.record_action(
                        unit_id=unit_id,
                        action_type="attack",
                        source_coord=source_coord,
                        target_coord=target_unit.coord,
                        target_unit_id=target_id,
                        damage_dealt=damage,
                        success=success
                    )
                else:
                    self._visualizer.record_action(
                        unit_id=unit_id,
                        action_type="attack",
                        source_coord=source_coord,
                        success=False
                    )
                    
            else:  # pass or unknown action
                self._visualizer.record_action(
                    unit_id=unit_id,
                    action_type=action_type,
                    source_coord=source_coord,
                    success=True
                )

    def _determine_winner(self) -> str | None:
        """Determine the winner of the game."""
        team_a_defeated = self._game_state.is_team_defeated(self._agents[0].team_id)
        team_b_defeated = self._game_state.is_team_defeated(self._agents[1].team_id)
        
        if team_a_defeated and not team_b_defeated:
            return self._agents[1].team_id
        elif team_b_defeated and not team_a_defeated:
            return self._agents[0].team_id
        else:
            return None  # Draw or both defeated

    def _determine_win_reason(self, max_turns: int) -> str:
        """Determine the reason for game ending."""
        team_a_defeated = self._game_state.is_team_defeated(self._agents[0].team_id)
        team_b_defeated = self._game_state.is_team_defeated(self._agents[1].team_id)
        
        if team_a_defeated and team_b_defeated:
            return "Both teams eliminated"
        elif team_a_defeated:
            return f"{self._agents[0].team_id} eliminated"
        elif team_b_defeated:
            return f"{self._agents[1].team_id} eliminated"
        elif self._turn_counter >= max_turns:
            return f"Turn limit reached ({max_turns} turns)"
        else:
            return "Game ended"

    # ------------------------ Printing Helpers -------------------------- #

    def _print_banner(self) -> None:
        print("==============================================")
        print("   HARFORD COUNTY CLASH – LLM vs LLM SHOWDOWN  ")
        print("==============================================")

    def _print_spectator_summary(self, validation_reports: List[str]) -> None:
        """
        Very concise spectator output so early development is readable.
        Will become more elaborate once GameState supports rich summaries.
        """
        # Header
        print("- Units --------------------------------------------------")
        # Columns:   TEAM | UNIT_ID | (x,y) | HP
        for unit in self._game_state.units.values():
            coord = f"({unit.coord.x},{unit.coord.y})"
            print(f"{unit.team_id:15} | {unit.id:8} | {coord:7} | HP:{unit.hp}")

        # Validation warnings
        for msg in validation_reports:
            print(f"[RULE] {msg}")

    def _print_final_scoreboard(self) -> None:
        duration = time.time() - self._start_wall_clock
        print("\n=================  FINAL  ======================")
        for agent in self._agents:
            status = "DEFEATED" if self._game_state.is_team_defeated(agent.team_id) else "ACTIVE"
            print(f"{agent.name:15} – {status}")
        print("================================================")
        print(f"Simulation completed in {duration:.2f}s")

    # ------------------------ Victory Logic ----------------------------- #

    def _check_victory_conditions(self, max_turns: int) -> bool:
        """
        Returns True when the game should terminate (victory or draw).
        A simple implementation that looks only at team elimination or
        turn cap.  Advanced resource-score tiebreakers to be added later.
        """
        team_a_defeated = self._game_state.is_team_defeated(self._agents[0].team_id)
        team_b_defeated = self._game_state.is_team_defeated(self._agents[1].team_id)

        if team_a_defeated and team_b_defeated:
            print("Both teams defeated – stalemate!")
            return True
        if team_a_defeated:
            print(f"{self._agents[1].name} wins by elimination!")
            return True
        if team_b_defeated:
            print(f"{self._agents[0].name} wins by elimination!")
            return True

        if self._turn_counter >= max_turns:
            print("Turn cap reached – declaring a draw (future: compare resources).")
            return True
        return False