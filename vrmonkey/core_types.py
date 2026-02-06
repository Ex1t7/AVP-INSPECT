

import json
import time
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Set


@dataclass
class Button:
    
    id: str
    content: str
    bbox: List[float]  
    interactivity: bool
    source: str

    def get_center(self, screen_width: int, screen_height: int) -> Tuple[int, int]:
        
        x_min, y_min, x_max, y_max = self.bbox
        target_x = int((x_min + x_max) / 2 * screen_width)
        target_y = int((y_min + y_max) / 2 * screen_height)
        return target_x, target_y


class State:
    

    def __init__(self, buttons: List[Button], screen_width: int = 3024, screen_height: int = 1964):
        self.buttons = buttons

        
        center_x = screen_width / 2
        center_y = screen_height / 2

        def distance_to_center(button: Button) -> float:
            
            btn_center_x = (button.bbox[0] + button.bbox[2]) / 2 * screen_width
            btn_center_y = (button.bbox[1] + button.bbox[3]) / 2 * screen_height
            return ((btn_center_x - center_x) ** 2 + (btn_center_y - center_y) ** 2) ** 0.5

        
        self.unexplored_buttons = sorted(buttons.copy(), key=distance_to_center)
        self.state_id = self._generate_state_id()

    def _generate_state_id(self) -> str:
        
        button_info = [(b.content, b.bbox) for b in self.buttons]
        return json.dumps(button_info, sort_keys=True)

    def has_unexplored_buttons(self) -> bool:
        
        return len(self.unexplored_buttons) > 0

    def get_next_unexplored_button(self) -> Optional[Button]:
        
        if self.has_unexplored_buttons():
            return self.unexplored_buttons.pop(0)
        return None

    def get_back_button(self) -> Optional[Button]:
        
        back_keywords = ['back', 'return', 'previous', 'close', 'cancel']
        for button in self.buttons:
            if any(keyword in button.content.lower() for keyword in back_keywords):
                return button
        return None

    def get_top_left_button(self) -> Optional[Button]:
        
        if not self.buttons:
            return None
        return min(self.buttons, key=lambda b: (b.bbox[1], b.bbox[0]))


@dataclass
class MouseRatioData:
    
    effective_ratio_x: float
    effective_ratio_y: float
    distance: float
    attempts: int
    timestamp: float


@dataclass
class MetricsData:
    
    start_time: float
    timeout_seconds: float
    states_found: int = 0
    states_explored: int = 0
    buttons_found: int = 0
    buttons_explored: int = 0
    pointer_moves_success: int = 0
    pointer_moves_failed: int = 0
    pointer_move_accuracy: List[float] = None

    def __post_init__(self):
        if self.pointer_move_accuracy is None:
            self.pointer_move_accuracy = []

    def is_timeout_reached(self) -> bool:
        
        elapsed_time = time.time() - self.start_time
        return elapsed_time >= self.timeout_seconds

    def get_remaining_time(self) -> float:
        
        elapsed_time = time.time() - self.start_time
        return max(0, self.timeout_seconds - elapsed_time)

    def get_elapsed_time(self) -> float:
        
        return time.time() - self.start_time

    def get_average_accuracy(self) -> float:
        
        if not self.pointer_move_accuracy:
            return 0.0
        return sum(self.pointer_move_accuracy) / len(self.pointer_move_accuracy)


@dataclass
class ScreenshotResult:
    
    success: bool
    file_path: Optional[str]
    timestamp: str
    error_message: Optional[str] = None


@dataclass
class PointerMoveResult:
    
    success: bool
    final_x: Optional[int]
    final_y: Optional[int]
    accuracy: Optional[float] = None
    attempts: Optional[int] = None
    error_message: Optional[str] = None
    password_detected: bool = False  


@dataclass
class AppCacheEntry:
    
    page: int
    timestamp: float

    def is_stale(self, max_age_hours: int = 24) -> bool:
        
        age_seconds = time.time() - self.timestamp
        return age_seconds > (max_age_hours * 3600)


class StateGraphEdge:
    

    def __init__(self, from_state_id: str, to_state_id: str, button: Button):
        self.from_state_id = from_state_id
        self.to_state_id = to_state_id
        self.button = button
        self.traversal_count = 0
        self.last_traversed = time.time()

    def record_traversal(self):
        
        self.traversal_count += 1
        self.last_traversed = time.time()