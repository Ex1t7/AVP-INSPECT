"""State graph management and similarity detection."""

import json
import logging
from typing import List, Dict, Optional, Tuple, Set

from core_types import State, Button, StateGraphEdge


class StateGraph:
    """Manages the graph of application states and transitions."""

    def __init__(self):
        self.nodes: List[State] = []
        self.edges: Dict[Tuple[str, str], StateGraphEdge] = {}
        self.dead_buttons: Set[Tuple[str, str]] = set()
        self.home_state: Optional[State] = None  # Store the initial/home state
        self.logger = logging.getLogger(__name__)

    def add_state(self, state: State) -> bool:
        """
        Add a new state to the graph if it doesn't already exist.

        Args:
            state: State to add

        Returns:
            True if state was added (new), False if it already existed
        """
        if self.has_state(state):
            return False

        self.nodes.append(state)
        self.logger.debug(f"Added new state to graph: {len(self.nodes)} total states")
        return True

    def add_edge(self, from_state: State, to_state: State, button: Button) -> None:
        """Add or update an edge between two states."""
        edge_key = (from_state.state_id, to_state.state_id)

        if edge_key in self.edges:
            # Update existing edge
            self.edges[edge_key].record_traversal()
        else:
            # Create new edge
            edge = StateGraphEdge(from_state.state_id, to_state.state_id, button)
            edge.record_traversal()
            self.edges[edge_key] = edge

        self.logger.debug(f"Added/updated edge: {from_state.state_id[:8]}... -> {to_state.state_id[:8]}...")

    def has_state(self, state: State) -> bool:
        """Check if a state already exists in the graph."""
        return any(self.check_same_states(state, existing_state)
                  for existing_state in self.nodes)

    def get_state_by_id(self, state_id: str) -> Optional[State]:
        """Get a state by its ID."""
        for state in self.nodes:
            if state.state_id == state_id:
                return state
        return None

    def find_similar_state(self, state: State) -> Optional[State]:
        """Find a similar state in the graph."""
        for existing_state in self.nodes:
            if self.check_same_states(state, existing_state):
                return existing_state
        return None

    def add_dead_button(self, state_id: str, button_id: str) -> None:
        """Mark a button as leading to a dead loop."""
        self.dead_buttons.add((state_id, button_id))
        self.logger.info(f"Marked button {button_id} in state {state_id[:8]}... as dead")

    def is_dead_button(self, state_id: str, button_id: str) -> bool:
        """Check if a button leads to a dead loop."""
        return (state_id, button_id) in self.dead_buttons

    def set_home_state(self, state: State) -> None:
        """Set the initial/home state of the application."""
        self.home_state = state
        self.logger.info(f"Set home state: {state.state_id[:16]}...")

    def is_home_state(self, state: State) -> bool:
        """Check if the given state is the home state."""
        if self.home_state is None:
            return False
        return self.check_same_states(state, self.home_state)

    def find_path_to_state(self, from_state: State, to_state: State) -> Optional[List[Button]]:
        """
        Find a sequence of buttons to click to get from from_state to to_state.

        Args:
            from_state: Starting state
            to_state: Target state

        Returns:
            List of buttons to click, or None if no path exists
        """
        if from_state == to_state:
            return []

        # Use BFS to find the shortest path
        queue = [(from_state, [])]  # (state, path)
        visited = {from_state.state_id}

        while queue:
            current_state, path = queue.pop(0)

            # Check all edges from current state
            for edge_key, edge in self.edges.items():
                from_id, to_id = edge_key
                if from_id == current_state.state_id:
                    next_state = self.get_state_by_id(to_id)
                    if next_state and next_state.state_id not in visited:
                        new_path = path + [edge.button]
                        if next_state == to_state:
                            return new_path
                        visited.add(next_state.state_id)
                        queue.append((next_state, new_path))

        return None

    def get_unexplored_states(self) -> List[State]:
        """Get all states that have unexplored buttons."""
        unexplored_states = []
        for state in self.nodes:
            if state.has_unexplored_buttons():
                # Check if any unexplored button is not dead
                for button in state.unexplored_buttons:
                    if not self.is_dead_button(state.state_id, button.id):
                        unexplored_states.append(state)
                        break
        return unexplored_states

    def get_stats(self) -> Dict[str, int]:
        """Get graph statistics."""
        total_buttons = sum(len(state.buttons) for state in self.nodes)
        total_unexplored = sum(len(state.unexplored_buttons) for state in self.nodes)
        total_dead_buttons = len(self.dead_buttons)

        return {
            'total_states': len(self.nodes),
            'total_edges': len(self.edges),
            'total_buttons': total_buttons,
            'unexplored_buttons': total_unexplored,
            'dead_buttons': total_dead_buttons,
            'exploration_progress': ((total_buttons - total_unexplored) / total_buttons * 100
                                   if total_buttons > 0 else 0)
        }

    @staticmethod
    def levenshtein_distance(s1: str, s2: str) -> int:
        """Calculate the Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return StateGraph.levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    @staticmethod
    def text_similarity(s1: str, s2: str) -> float:
        """
        Calculate text similarity between two strings using combined
        Levenshtein and semantic similarity.

        Args:
            s1: First string
            s2: Second string

        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not s1 or not s2:
            return 0.0

        # Normalize strings for comparison
        s1 = s1.lower().strip()
        s2 = s2.lower().strip()

        # Exact match
        if s1 == s2:
            return 1.0

        # Calculate Levenshtein similarity
        distance = StateGraph.levenshtein_distance(s1, s2)
        max_len = max(len(s1), len(s2))
        levenshtein_sim = 1.0 - (distance / max_len) if max_len > 0 else 0.0

        # Check for common OCR confusions
        ocr_confusions = {
            '0': 'o', '1': 'i', '2': 'z', '5': 's', '8': 'b', '9': 'g',
            'l': 'i', 'i': 'l', 'o': '0', 'z': '2', 's': '5', 'b': '8', 'g': '9'
        }

        # Try replacing common OCR confusions
        best_sim = levenshtein_sim
        for char, replacement in ocr_confusions.items():
            s1_alt = s1.replace(char, replacement)
            s2_alt = s2.replace(char, replacement)
            if s1_alt != s1 or s2_alt != s2:
                alt_distance = StateGraph.levenshtein_distance(s1_alt, s2_alt)
                alt_sim = 1.0 - (alt_distance / max_len) if max_len > 0 else 0.0
                best_sim = max(best_sim, alt_sim)

        # Check for common OCR patterns
        common_patterns = [
            ('rn', 'm'), ('cl', 'd'), ('vv', 'w'), ('nn', 'm'),
            ('ii', 'n'), ('il', 'n'), ('li', 'n')
        ]

        for pattern, replacement in common_patterns:
            s1_alt = s1.replace(pattern, replacement)
            s2_alt = s2.replace(pattern, replacement)
            if s1_alt != s1 or s2_alt != s2:
                alt_distance = StateGraph.levenshtein_distance(s1_alt, s2_alt)
                alt_sim = 1.0 - (alt_distance / max_len) if max_len > 0 else 0.0
                best_sim = max(best_sim, alt_sim)

        # Check for semantic similarity in common UI elements
        semantic_groups = {
            'back': ['back', 'return', 'previous', 'go back'],
            'next': ['next', 'continue', 'proceed', 'forward'],
            'cancel': ['cancel', 'close', 'exit', 'quit'],
            'ok': ['ok', 'confirm', 'accept', 'yes'],
            'settings': ['settings', 'options', 'preferences', 'configuration'],
            'help': ['help', 'support', 'assistance', 'guide']
        }

        # Check if both strings belong to the same semantic group
        semantic_sim = 0.0
        for group, words in semantic_groups.items():
            if s1 in words and s2 in words:
                semantic_sim = 1.0
                break

        # Combine Levenshtein and semantic similarity
        if semantic_sim > 0.8:
            return 0.7 * semantic_sim + 0.3 * best_sim
        else:
            return best_sim

    @staticmethod
    def check_same_states(state1: State, state2: State, tolerance: float = 0.7) -> bool:
        """
        Compare two states to determine if they are equivalent using
        text similarity of button contents.

        Args:
            state1: First state
            state2: Second state
            tolerance: Similarity threshold (0.0 to 1.0)

        Returns:
            True if states are considered the same
        """
        if len(state1.buttons) == 0 and len(state2.buttons) == 0:
            return True

        if len(state1.buttons) == 0 or len(state2.buttons) == 0:
            return False

        # Get lists of button contents
        contents1 = [b.content for b in state1.buttons]
        contents2 = [b.content for b in state2.buttons]

        # If significantly different number of buttons, likely different states
        size_ratio = min(len(contents1), len(contents2)) / max(len(contents1), len(contents2))
        if size_ratio < 0.7:  # More than 30% difference in button count
            return False

        # Calculate similarity scores between all pairs
        similarity_scores = []
        for c1 in contents1:
            max_similarity = 0
            for c2 in contents2:
                similarity = StateGraph.text_similarity(c1, c2)
                max_similarity = max(max_similarity, similarity)
            similarity_scores.append(max_similarity)

        # Calculate average similarity
        avg_similarity = sum(similarity_scores) / len(similarity_scores) if similarity_scores else 0

        # Return True if average similarity is above the tolerance threshold
        result = avg_similarity >= tolerance
        return result

    def print_graph_structure(self) -> str:
        """Generate a string representation of the graph structure."""
        graph_str = "\n=== State Graph Structure ===\n"
        graph_str += f"Total States: {len(self.nodes)}\n"
        graph_str += f"Total Edges: {len(self.edges)}\n"
        graph_str += f"Dead Buttons: {len(self.dead_buttons)}\n\n"

        # Print states
        graph_str += "States:\n"
        for i, state in enumerate(self.nodes):
            graph_str += f"State {i} (ID: {state.state_id[:16]}...):\n"
            graph_str += f"  Total buttons: {len(state.buttons)}\n"
            graph_str += f"  Unexplored buttons: {len(state.unexplored_buttons)}\n"
            for j, button in enumerate(state.buttons[:5]):  # Show first 5 buttons
                status = "unexplored" if button in state.unexplored_buttons else "explored"
                graph_str += f"    Button {j}: '{button.content}' ({status})\n"
            if len(state.buttons) > 5:
                graph_str += f"    ... and {len(state.buttons) - 5} more buttons\n"
            graph_str += "\n"

        # Print edges
        graph_str += "Transitions:\n"
        for edge_key, edge in self.edges.items():
            from_id, to_id = edge_key
            from_state = self.get_state_by_id(from_id)
            to_state = self.get_state_by_id(to_id)

            if from_state and to_state:
                from_idx = self.nodes.index(from_state)
                to_idx = self.nodes.index(to_state)
                graph_str += (f"State {from_idx} -> State {to_idx} "
                            f"via button: '{edge.button.content}' "
                            f"(traversed {edge.traversal_count} times)\n")

        graph_str += "=" * 30 + "\n"
        return graph_str

    def export_to_json(self) -> Dict:
        """Export the graph to a JSON-serializable format."""
        states_data = []
        for i, state in enumerate(self.nodes):
            state_data = {
                'index': i,
                'state_id': state.state_id,
                'total_buttons': len(state.buttons),
                'unexplored_buttons': len(state.unexplored_buttons),
                'buttons': [
                    {
                        'id': button.id,
                        'content': button.content,
                        'bbox': button.bbox,
                        'source': button.source,
                        'explored': button not in state.unexplored_buttons
                    }
                    for button in state.buttons
                ]
            }
            states_data.append(state_data)

        edges_data = []
        for edge_key, edge in self.edges.items():
            from_id, to_id = edge_key
            from_state = self.get_state_by_id(from_id)
            to_state = self.get_state_by_id(to_id)

            if from_state and to_state:
                edge_data = {
                    'from_state_index': self.nodes.index(from_state),
                    'to_state_index': self.nodes.index(to_state),
                    'button_content': edge.button.content,
                    'button_id': edge.button.id,
                    'traversal_count': edge.traversal_count,
                    'last_traversed': edge.last_traversed
                }
                edges_data.append(edge_data)

        return {
            'stats': self.get_stats(),
            'states': states_data,
            'edges': edges_data,
            'dead_buttons': list(self.dead_buttons)
        }