#!/usr/bin/env python

from enum import Enum
import math
import time

MoveResult = tuple[list[float], list[float], str | None]


class GripperState(Enum):
    OPEN = 0
    CLOSED = 1

class Robot():

    def __init__(self, initial_position: list[float] | None = None, home_position: list[float] | None = None, gripper_state: GripperState = GripperState.OPEN):

        self.current_position: list[float] = list(initial_position) if initial_position is not None else [0, 0, 0]
        self.home_position: list[float] = list(home_position) if home_position is not None else [0, 0, 0]
        self.gripper_state: GripperState = gripper_state
        self.last_motion_time: float = 0
        self.axis_speed: list[float] = [0, 0, 0]
        self.robot_limits: list[float] = [1000, 1000, 1000]

    def _plan_motion(self, target_position: list[float], speed: int) -> list[float]:
        delta = [target_position[i] - self.current_position[i] for i in range(len(self.current_position))]
        control_axis_distance = max(delta, key=abs) 
        motion_time = abs(control_axis_distance) / speed
        axis_speed = [i/motion_time for i in delta]

        return axis_speed
    
    def _same_position(self,target_position: list[float]) -> bool :
        return all(math.isclose(target_position[i], self.current_position[i], abs_tol=1e-9) for i in range(len(self.current_position)))

    def _is_motion_completed(self, target_position: list[float]) -> bool :
        for i,j in enumerate(target_position):
            remaining = j - self.current_position[i]
            speed = self.axis_speed[i]
            if (remaining > 0 and speed > 0) or (remaining < 0 and speed < 0):
                return False
        return True

    def move_to(self, target_position: list[float], speed: int = 90) -> MoveResult:

        if not (0 < speed <= 100) : return self.current_position, self.axis_speed, f"Requested speed of : {speed} mm/s is outside of the limits (0,100]"
        if len(target_position) != len(self.current_position):
            return self.current_position, self.axis_speed, f"Requested position must have {len(self.current_position)} axes, got {len(target_position)}"
        for i,j in enumerate(target_position) :
            if j > self.robot_limits[i] or j < -self.robot_limits[i] :
                return self.current_position, self.axis_speed, f"Requested position of : {j} for axis {i} is outside of the limits {self.robot_limits}"

        if self._same_position(target_position): return self.current_position, self.axis_speed, None

        actual_time = time.perf_counter()

        if all(v == 0 for v in self.axis_speed):
            self.axis_speed = self._plan_motion(target_position, speed)
            self.last_motion_time = actual_time

        delta_t = actual_time - self.last_motion_time

        self.current_position = [self.current_position[i] + delta_t * self.axis_speed[i] for i in range(len(self.current_position))]
 
        self.last_motion_time = time.perf_counter()

        if self._is_motion_completed(target_position):
            self.axis_speed = [0,0,0]
            self.current_position = list(target_position)

        return self.current_position, self.axis_speed, None

    def close_gripper(self) -> GripperState:
        self.gripper_state = GripperState.CLOSED
        return self.gripper_state

    def open_gripper(self) -> GripperState:
        self.gripper_state = GripperState.OPEN
        return self.gripper_state

    def move_home(self, speed: int = 50) -> MoveResult:
        return self.move_to(self.home_position, speed)


if __name__=='__main__':
    pass