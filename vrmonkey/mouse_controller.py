

import time
import logging
from typing import Optional, Tuple, List

from config import Config
from core_types import PointerMoveResult, MouseRatioData
from esp32_mouse import ESP32Mouse
import pointer_recognize
from password_input_detector import quick_test


class MouseController:
    

    def __init__(self, config: Config, esp32: ESP32Mouse):
        self.config = config
        self.esp32 = esp32
        self.logger = logging.getLogger(__name__)

        
        self.mouse_ratio: Tuple[float, float] = (0.60, 0.91)  
        self.ratio_history: List[MouseRatioData] = []
        self.consecutive_failures = 0

        
        self.consecutive_no_movement = 0
        self.last_pointer_position: Optional[Tuple[int, int]] = None

    def find_pointer(self, screenshot_path: str) -> Optional[Tuple[int, int]]:
        
        try:
            pointer = pointer_recognize.find_pointer_centers(screenshot_path)
            return pointer
        except Exception as e:
            self.logger.error(f"Error finding pointer: {e}")
            return None

    def _check_password_input(self, screenshot_path: str) -> bool:
        
        try:
            is_password = quick_test(screenshot_path)
            if is_password:
                self.logger.warning("🔐 Password input dialog detected!")
            return is_password
        except Exception as e:
            self.logger.error(f"Error checking for password input: {e}")
            return False

    def move_pixel(self, x: int, y: int) -> bool:
        
        try:
            
            x_sign = 1 if x == 0 else int(abs(x) / x)
            y_sign = 1 if y == 0 else int(abs(y) / y)

            
            x = int(x * self.mouse_ratio[0])
            y = int(y * self.mouse_ratio[1])

            
            step20 = self.config.mouse.step20
            step10 = self.config.mouse.step10

            move_x_20_times = int(abs(x) / step20)
            move_x_10_times = int((abs(x) % step20) / step10)
            move_x_1_times = int((abs(x) % step10) / 1)

            move_y_20_times = int(abs(y) / step20)
            move_y_10_times = int((abs(y) % step20) / step10)
            move_y_1_times = int((abs(y) % step10) / 1)

            
            if (move_x_20_times == 0 and move_x_10_times == 0 and
                    move_y_20_times == 0 and move_y_10_times == 0):
                if move_x_1_times != 0:
                    if not self.esp32.move_mouse(x_sign * move_x_1_times, 0):
                        self.logger.error(f"Failed to move mouse by {x_sign * move_x_1_times} pixels")
                        return False

                if move_y_1_times != 0:
                    if not self.esp32.move_mouse(0, y_sign * move_y_1_times):
                        self.logger.error(f"Failed to move mouse by {y_sign * move_y_1_times} pixels")
                        return False

                time.sleep(0.1)
                self._bounce_leg()
                return True

            
            
            for _ in range(move_x_20_times):
                if not self.esp32.move_mouse(x_sign * 20, 0):
                    self.logger.error(f"Failed to move mouse by {x_sign * 20} pixels")
                    return False

            for _ in range(move_x_10_times):
                if not self.esp32.move_mouse(x_sign * 10, 0):
                    self.logger.error(f"Failed to move mouse by {x_sign * 10} pixels")
                    return False

            
            if move_x_1_times != 0:
                if not self.esp32.move_mouse(x_sign * move_x_1_times, 0):
                    self.logger.error(f"Failed to move mouse by {x_sign * move_x_1_times} pixels")
                    return False

            
            for _ in range(move_y_20_times):
                if not self.esp32.move_mouse(0, y_sign * 20):
                    self.logger.error(f"Failed to move mouse by {y_sign * 20} pixels")
                    return False

            for _ in range(move_y_10_times):
                if not self.esp32.move_mouse(0, y_sign * 10):
                    self.logger.error(f"Failed to move mouse by {y_sign * 10} pixels")
                    return False

            
            if move_y_1_times != 0:
                if not self.esp32.move_mouse(0, y_sign * move_y_1_times):
                    self.logger.error(f"Failed to move mouse by {y_sign * move_y_1_times} pixels")
                    return False

            time.sleep(0.1)
            self._bounce_leg()
            return True

        except Exception as e:
            self.logger.error(f"Error in move_pixel: {e}")
            return False

    def move_to_target(self, target_x: int, target_y: int,
                       screenshot_manager,
                       tolerance: Optional[int] = 10) -> PointerMoveResult:
        
        if tolerance is None:
            tolerance = self.config.mouse.tolerance

        max_attempts = self.config.mouse.max_attempts
        attempts = 0
        lost_pointer_count = 0
        max_lost_pointer = self.config.exploration.max_lost_pointer_count

        self.logger.debug(f"Moving to target: ({target_x}, {target_y})")

        
        self._bounce_leg()

        
        screenshot_result = screenshot_manager.take_screenshot()
        if not screenshot_result.success:
            return PointerMoveResult(
                success=False,
                final_x=None,
                final_y=None,
                error_message="Failed to take initial screenshot"
            )

        pointer_pos = self.find_pointer(screenshot_result.file_path)
        if pointer_pos is None:
            
            if self._check_password_input(screenshot_result.file_path):
                self.logger.warning("Lost pointer due to password input dialog")
                self.consecutive_failures += 1
                return PointerMoveResult(
                    success=False,
                    final_x=None,
                    final_y=None,
                    error_message="Password input dialog detected",
                    password_detected=True
                )

            
            if not self._recover_pointer(screenshot_manager):
                self.consecutive_failures += 1
                return PointerMoveResult(
                    success=False,
                    final_x=None,
                    final_y=None,
                    error_message="Could not find or recover pointer"
                )

            
            screenshot_result = screenshot_manager.take_screenshot()
            if not screenshot_result.success:
                return PointerMoveResult(
                    success=False,
                    final_x=None,
                    final_y=None,
                    error_message="Failed to take screenshot after recovery"
                )

            pointer_pos = self.find_pointer(screenshot_result.file_path)
            if pointer_pos is None:
                
                if self._check_password_input(screenshot_result.file_path):
                    self.logger.warning("Lost pointer due to password input dialog (after recovery)")
                    self.consecutive_failures += 1
                    return PointerMoveResult(
                        success=False,
                        final_x=None,
                        final_y=None,
                        error_message="Password input dialog detected after recovery",
                        password_detected=True
                    )

                self.consecutive_failures += 1
                return PointerMoveResult(
                    success=False,
                    final_x=None,
                    final_y=None,
                    error_message="Still cannot find pointer after recovery"
                )

        initial_x, initial_y = pointer_pos
        x_now, y_now = initial_x, initial_y
        self.logger.debug(f"Starting position: ({x_now}, {y_now})")

        
        delta_x = target_x - x_now
        delta_y = target_y - y_now

        
        
        move_step_x = abs(delta_x) / self.mouse_ratio[0] if self.mouse_ratio[0] > 0 else abs(delta_x)
        move_step_y = abs(delta_y) / self.mouse_ratio[1] if self.mouse_ratio[1] > 0 else abs(delta_y)
        x_direction = 1 if delta_x > 0 else -1
        y_direction = 1 if delta_y > 0 else -1

        
        total_x_movement = 0
        total_y_movement = 0

        
        while abs(delta_x) > tolerance or abs(delta_y) > tolerance:
            
            x_step = move_step_x * x_direction
            y_step = move_step_y * y_direction

            
            total_x_movement += x_step
            total_y_movement += y_step

            
            if not self.move_pixel(x_step, y_step):
                self.logger.error(f"Failed to move mouse by ({x_step}, {y_step})")
                self.consecutive_failures += 1
                return PointerMoveResult(
                    success=False,
                    final_x=x_now,
                    final_y=y_now,
                    attempts=attempts,
                    error_message="Mouse movement failed"
                )

            
            screenshot_result = screenshot_manager.take_screenshot()
            if not screenshot_result.success:
                return PointerMoveResult(
                    success=False,
                    final_x=x_now,
                    final_y=y_now,
                    attempts=attempts,
                    error_message="Failed to take screenshot during movement"
                )

            pointer_pos = self.find_pointer(screenshot_result.file_path)
            if pointer_pos is None:
                
                if self._check_password_input(screenshot_result.file_path):
                    self.logger.warning("Lost pointer during movement due to password input dialog")
                    return PointerMoveResult(
                        success=False,
                        final_x=None,
                        final_y=None,
                        attempts=attempts,
                        error_message="Password input dialog detected during movement",
                        password_detected=True
                    )

                lost_pointer_count += 1
                self.logger.warning(f"Lost pointer during movement (attempt {lost_pointer_count})")

                if lost_pointer_count >= max_lost_pointer:
                    return PointerMoveResult(
                        success=False,
                        final_x=None,
                        final_y=None,
                        attempts=attempts,
                        error_message=f"Pointer lost {lost_pointer_count} times"
                    )

                if not self._recover_pointer(screenshot_manager):
                    continue

                
                screenshot_result = screenshot_manager.take_screenshot()
                if screenshot_result.success:
                    pointer_pos = self.find_pointer(screenshot_result.file_path)
                    if pointer_pos is None:
                        
                        if self._check_password_input(screenshot_result.file_path):
                            self.logger.warning("Password input detected after recovery attempt")
                            return PointerMoveResult(
                                success=False,
                                final_x=None,
                                final_y=None,
                                attempts=attempts,
                                error_message="Password input dialog detected after recovery",
                                password_detected=True
                            )
                        continue
            else:
                lost_pointer_count = 0  

            
            prev_x, prev_y = x_now, y_now
            x_now, y_now = pointer_pos

            
            distance_moved = ((x_now - prev_x) ** 2 + (y_now - prev_y) ** 2) ** 0.5
            if distance_moved <= 5:  
                self.consecutive_no_movement += 1
                self.logger.warning(f"⚠️ Pointer didn't move! ({distance_moved:.1f}px) - Count: {self.consecutive_no_movement}")

                
                if self.consecutive_no_movement >= 2:  
                    self.logger.info("Attempting to recover stuck pointer...")
                    if self._recover_pointer(screenshot_manager):
                        
                        screenshot_result = screenshot_manager.take_screenshot()
                        if screenshot_result.success:
                            recovered_pos = self.find_pointer(screenshot_result.file_path)
                            if recovered_pos:
                                x_now, y_now = recovered_pos
                                self.consecutive_no_movement = 0  
                                self.logger.info(f"Pointer recovered to ({x_now}, {y_now})")
                                
                            else:
                                self.logger.warning("Could not find pointer after recovery")

                
                max_no_movement = self.config.exploration.max_no_movement_attempts
                if self.consecutive_no_movement >= max_no_movement:
                    self.logger.error(f"🚫 Pointer stuck after {self.consecutive_no_movement} attempts!")
                    return PointerMoveResult(
                        success=False,
                        final_x=x_now,
                        final_y=y_now,
                        attempts=attempts,
                        error_message=f"Pointer stuck - no movement for {self.consecutive_no_movement} attempts"
                    )
            else:
                
                self.consecutive_no_movement = 0
                self.last_pointer_position = (x_now, y_now)

            
            prev_delta_x = delta_x
            prev_delta_y = delta_y
            delta_x = target_x - x_now
            delta_y = target_y - y_now

            
            
            if delta_x * x_direction < 0:
                
                x_direction = -x_direction
                move_step_x = max(tolerance, move_step_x / 2)
                self.logger.debug(f"X overshoot, halving step to {move_step_x:.1f}")
            elif abs(delta_x) < abs(prev_delta_x) * 0.5:
                
                
                move_step_x = max(move_step_x, abs(delta_x) / self.mouse_ratio[0] if self.mouse_ratio[0] > 0 else abs(delta_x))
                x_direction = 1 if delta_x > 0 else -1
                self.logger.debug(f"X good progress, step size: {move_step_x:.1f}")
            elif abs(delta_x) > abs(prev_delta_x) * 0.9:
                
                move_step_x = min(move_step_x * 1.5, abs(delta_x) / self.mouse_ratio[0] if self.mouse_ratio[0] > 0 else abs(delta_x))
                x_direction = 1 if delta_x > 0 else -1
                self.logger.debug(f"X slow progress, increasing step to {move_step_x:.1f}")
            else:
                
                move_step_x = abs(delta_x) / self.mouse_ratio[0] if self.mouse_ratio[0] > 0 else abs(delta_x)
                x_direction = 1 if delta_x > 0 else -1

            
            if delta_y * y_direction < 0:
                
                y_direction = -y_direction
                move_step_y = max(tolerance, move_step_y / 2)
                self.logger.debug(f"Y overshoot, halving step to {move_step_y:.1f}")
            elif abs(delta_y) < abs(prev_delta_y) * 0.5:
                
                move_step_y = max(move_step_y, abs(delta_y) / self.mouse_ratio[1] if self.mouse_ratio[1] > 0 else abs(delta_y))
                y_direction = 1 if delta_y > 0 else -1
                self.logger.debug(f"Y good progress, step size: {move_step_y:.1f}")
            elif abs(delta_y) > abs(prev_delta_y) * 0.9:
                
                move_step_y = min(move_step_y * 1.5, abs(delta_y) / self.mouse_ratio[1] if self.mouse_ratio[1] > 0 else abs(delta_y))
                y_direction = 1 if delta_y > 0 else -1
                self.logger.debug(f"Y slow progress, increasing step to {move_step_y:.1f}")
            else:
                
                move_step_y = abs(delta_y) / self.mouse_ratio[1] if self.mouse_ratio[1] > 0 else abs(delta_y)
                y_direction = 1 if delta_y > 0 else -1

            attempts += 1
            if attempts > max_attempts:
                self.logger.error(f"Movement failed after {max_attempts} attempts")
                self.consecutive_failures += 1
                return PointerMoveResult(
                    success=False,
                    final_x=x_now,
                    final_y=y_now,
                    attempts=attempts,
                    error_message=f"Max attempts ({max_attempts}) exceeded"
                )

            self.logger.debug(f"Attempt {attempts}: pos=({x_now}, {y_now}), "
                             f"target=({target_x}, {target_y}), "
                             f"step=({x_step}, {y_step})")

        
        final_x, final_y = x_now, y_now
        screen_width, screen_height = screenshot_manager.get_screen_dimensions()
        accuracy_x = 1 - abs(final_x - target_x) / screen_width
        accuracy_y = 1 - abs(final_y - target_y) / screen_height
        accuracy = (accuracy_x + accuracy_y) / 2 * 100

        
        self._update_ratio_from_movement(
            initial_x, initial_y, target_x, target_y,
            total_x_movement, total_y_movement, attempts
        )

        
        self.consecutive_failures = 0

        self.logger.info(f"Movement successful: attempts={attempts}, accuracy={accuracy:.2f}%")
        return PointerMoveResult(
            success=True,
            final_x=final_x,
            final_y=final_y,
            accuracy=accuracy,
            attempts=attempts
        )

    def _bounce_leg(self) -> bool:
        
        try:
            for _ in range(2):
                if not self.esp32.move_mouse(self.config.mouse.bouncing_leg_step, 0):
                    self.logger.warning("Failed to perform bounce leg movement")
                    return False
                time.sleep(0.1)

            
            self.config.mouse.bouncing_leg_step *= -1
            return True
        except Exception as e:
            self.logger.error(f"Error in bounce_leg: {e}")
            return False

    def _recover_pointer(self, screenshot_manager) -> bool:
        
        self.logger.info("Attempting to recover lost pointer")

        
        recovery_positions = [
            (-self.config.mouse.max_pixel, -self.config.mouse.max_pixel),  
            (self.config.mouse.max_pixel, self.config.mouse.max_pixel),   
            (-self.config.mouse.max_pixel, self.config.mouse.max_pixel),  
            (self.config.mouse.max_pixel, -self.config.mouse.max_pixel)   
        ]

        for x, y in recovery_positions:
            if self.move_pixel(x, y):
                time.sleep(0.5)
                screenshot_result = screenshot_manager.take_screenshot()
                if screenshot_result.success:
                    pointer_pos = self.find_pointer(screenshot_result.file_path)
                    if pointer_pos is not None:
                        self.logger.info("Successfully recovered pointer")
                        return True

        
        screen_width, screen_height = screenshot_manager.get_screen_dimensions()
        if self.move_pixel(screen_width // 2, screen_height // 2):
            time.sleep(0.5)
            screenshot_result = screenshot_manager.take_screenshot()
            if screenshot_result.success:
                pointer_pos = self.find_pointer(screenshot_result.file_path)
                if pointer_pos is not None:
                    self.logger.info("Successfully recovered pointer at center")
                    return True

        self.logger.error("Failed to recover pointer")
        return False

    def _update_ratio_from_movement(self, initial_x: int, initial_y: int,
                                   target_x: int, target_y: int,
                                   total_x_movement: int, total_y_movement: int,
                                   attempts: int):
        
        
        actual_delta_x = target_x - initial_x
        actual_delta_y = target_y - initial_y

        effective_ratio_x = (abs(actual_delta_x) / abs(total_x_movement)
                            if total_x_movement != 0 else self.mouse_ratio[0])
        effective_ratio_y = (abs(actual_delta_y) / abs(total_y_movement)
                            if total_y_movement != 0 else self.mouse_ratio[1])

        
        ratio_data = MouseRatioData(
            effective_ratio_x=effective_ratio_x,
            effective_ratio_y=effective_ratio_y,
            distance=abs(actual_delta_x) + abs(actual_delta_y),
            attempts=attempts,
            timestamp=time.time()
        )
        self.ratio_history.append(ratio_data)

        self.logger.debug(f"Effective ratios: x={effective_ratio_x:.3f}, y={effective_ratio_y:.3f}")

        
        if len(self.ratio_history) >= self.config.mouse.min_ratio_samples:
            self._apply_ratio_learning()

    def _apply_ratio_learning(self):
        
        
        recent_samples = self.ratio_history[-self.config.mouse.ratio_learning_samples:]

        
        x_ratios = [s.effective_ratio_x for s in recent_samples]
        y_ratios = [s.effective_ratio_y for s in recent_samples]

        x_ratios.sort()
        y_ratios.sort()
        median_ratio_x = x_ratios[len(x_ratios) // 2]
        median_ratio_y = y_ratios[len(y_ratios) // 2]

        
        x_mean = sum(x_ratios) / len(x_ratios)
        y_mean = sum(y_ratios) / len(y_ratios)
        x_std = (sum((x - x_mean) ** 2 for x in x_ratios) / len(x_ratios)) ** 0.5
        y_std = (sum((y - y_mean) ** 2 for y in y_ratios) / len(y_ratios)) ** 0.5

        
        if x_std < 0.1 and y_std < 0.1:
            rate = self.config.mouse.ratio_learning_rate
            new_ratio_x = self.mouse_ratio[0] * (1 - rate) + median_ratio_x * rate
            new_ratio_y = self.mouse_ratio[1] * (1 - rate) + median_ratio_y * rate
            self.mouse_ratio = (new_ratio_x, new_ratio_y)

            self.logger.info(f"Updated mouse ratio: {self.mouse_ratio} "
                           f"(std dev: x={x_std:.3f}, y={y_std:.3f})")
        else:
            self.logger.debug(f"Ratios too inconsistent, skipping update "
                            f"(std dev: x={x_std:.3f}, y={y_std:.3f})")

    def calibrate_ratio(self, screenshot_manager, delta_x: int = 500, delta_y: int = 500) -> bool:
        
        self.logger.info("Starting mouse ratio calibration")
        time.sleep(2)

        
        screenshot_result = screenshot_manager.take_screenshot()
        if not screenshot_result.success:
            self.logger.error("Failed to take initial calibration screenshot")
            return False

        initial_pos = self.find_pointer(screenshot_result.file_path)
        if initial_pos is None:
            self.logger.error("Cannot find pointer for calibration")
            return False

        x_now, y_now = initial_pos
        self.logger.info(f"Initial calibration position: ({x_now}, {y_now})")

        
        if not self.move_pixel(delta_x, delta_y):
            self.logger.error("Failed to perform calibration movement")
            return False

        time.sleep(2)

        
        screenshot_result = screenshot_manager.take_screenshot()
        if not screenshot_result.success:
            self.logger.error("Failed to take final calibration screenshot")
            return False

        final_pos = self.find_pointer(screenshot_result.file_path)
        if final_pos is None:
            self.logger.error("Cannot find pointer after calibration movement")
            return False

        x_target, y_target = final_pos
        self.logger.info(f"Final calibration position: ({x_target}, {y_target})")

        
        ratio_x = abs(x_target - x_now) / delta_x if delta_x != 0 else 1.0
        ratio_y = abs(y_target - y_now) / delta_y if delta_y != 0 else 1.0
        self.mouse_ratio = (ratio_x, ratio_y)

        self.logger.info(f"Calibrated mouse ratio: {self.mouse_ratio}")
        return True

    def get_consecutive_failures(self) -> int:
        
        return self.consecutive_failures

    def reset_consecutive_failures(self):
        
        self.consecutive_failures = 0

    def get_consecutive_no_movement(self) -> int:
        
        return self.consecutive_no_movement

    def reset_no_movement_counter(self):
        
        self.consecutive_no_movement = 0
        self.last_pointer_position = None