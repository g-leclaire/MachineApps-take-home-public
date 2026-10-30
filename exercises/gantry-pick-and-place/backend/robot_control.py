import asyncio
import logging
from collections.abc import Callable

from state_machine.core import StateMachine
from state_machine.defs import State, StateGroup, Trigger
from state_machine.decorators import on_enter_state, auto_timeout

from robot_sim import Robot

logger = logging.getLogger(__name__)


class PickPlace(StateGroup):
    homing_lifting = State()
    homing_traversing = State()
    homing_lowering = State()
    moving_to_cube_lifting = State()
    moving_to_cube_traversing = State()
    moving_to_cube_lowering = State()
    gripping = State()
    moving_to_destination_lifting = State()
    moving_to_destination_traversing = State()
    moving_to_destination_lowering = State()
    releasing = State()
    lifting_after_release = State()

class States:
    pick_place = PickPlace()

class Triggers:
    start = Trigger("start")
    home = Trigger("home")
    begin_sequence = Trigger("begin_sequence")
    finished_homing_lifting = Trigger("finished_homing_lifting")
    finished_homing_traversing = Trigger("finished_homing_traversing")
    finished_homing_lowering = Trigger("finished_homing_lowering")
    finished_moving_to_cube_lifting = Trigger("finished_moving_to_cube_lifting")
    finished_moving_to_cube_traversing = Trigger("finished_moving_to_cube_traversing")
    finished_moving_to_cube_lowering = Trigger("finished_moving_to_cube_lowering")
    finished_gripping = Trigger("finished_gripping")
    finished_moving_to_destination_lifting = Trigger("finished_moving_to_destination_lifting")
    finished_moving_to_destination_traversing = Trigger("finished_moving_to_destination_traversing")
    finished_moving_to_destination_lowering = Trigger("finished_moving_to_destination_lowering")
    finished_releasing = Trigger("finished_releasing")
    finished_lifting_after_release = Trigger("finished_lifting_after_release")
    to_fault = Trigger("to_fault")

TRANSITIONS = [
    Triggers.start.transition("ready", "ready"),
    Triggers.home.transition("ready", States.pick_place.homing_lifting),
    Triggers.home.transition("fault", States.pick_place.homing_lifting),
    Triggers.finished_homing_lifting.transition(States.pick_place.homing_lifting, States.pick_place.homing_traversing),
    Triggers.finished_homing_traversing.transition(States.pick_place.homing_traversing, States.pick_place.homing_lowering),
    Triggers.finished_homing_lowering.transition(States.pick_place.homing_lowering, "ready"),
    Triggers.begin_sequence.transition("ready", States.pick_place.moving_to_cube_lifting),
    Triggers.finished_moving_to_cube_lifting.transition(States.pick_place.moving_to_cube_lifting, States.pick_place.moving_to_cube_traversing),
    Triggers.finished_moving_to_cube_traversing.transition(States.pick_place.moving_to_cube_traversing, States.pick_place.moving_to_cube_lowering),
    Triggers.finished_moving_to_cube_lowering.transition(States.pick_place.moving_to_cube_lowering, States.pick_place.gripping),
    Triggers.finished_gripping.transition(States.pick_place.gripping, States.pick_place.moving_to_destination_lifting),
    Triggers.finished_moving_to_destination_lifting.transition(States.pick_place.moving_to_destination_lifting, States.pick_place.moving_to_destination_traversing),
    Triggers.finished_moving_to_destination_traversing.transition(States.pick_place.moving_to_destination_traversing, States.pick_place.moving_to_destination_lowering),
    Triggers.finished_moving_to_destination_lowering.transition(States.pick_place.moving_to_destination_lowering, States.pick_place.releasing),
    Triggers.finished_releasing.transition(States.pick_place.releasing, States.pick_place.lifting_after_release),
    Triggers.finished_lifting_after_release.transition(States.pick_place.lifting_after_release, "ready"),
]

class GantryMachine(StateMachine):
    cube_position = [-200.0, 200.0, 200.0]
    destination_position = [200.0, -200.0, 200.0]
    safe_travel_z = 300.0
    motion_speed = 100
    motion_poll_interval = 0.1

    def __init__(self, robot: Robot | None = None):
        self.robot = robot if robot is not None else Robot()
        self.last_error: str | None = None
        self.on_motion_update: Callable[[], None] | None = None
        super().__init__(
            states=States,
            transitions=TRANSITIONS,
            enable_last_state_recovery=False
        )

    def set_robot_position(self, initial_position: list[float]) -> None:
        self.robot = Robot(initial_position=list(initial_position))

    def set_target_positions(self, cube_position: list[float], destination_position: list[float]) -> None:
        self.cube_position = list(cube_position)
        self.destination_position = list(destination_position)

    @on_enter_state("ready")
    def clear_error(self, _):
        self.last_error = None

    @on_enter_state("fault")
    def enter_fault(self, _) -> None:
        self._clear_all_timeouts()
        for task in list(self._tasks):
            task.cancel()
        self.robot.axis_speed = [0, 0, 0]

    @on_enter_state(States.pick_place.homing_lifting)
    @auto_timeout(10.0, Triggers.to_fault)
    def enter_homing_lifting(self, _):
        logger.info("Entering homing_lifting")
        self.spawn(self._move_to(self._current_xy_at_safe_z(), Triggers.finished_homing_lifting))

    def _current_xy_at_safe_z(self) -> list[float]:
        return [self.robot.current_position[0], self.robot.current_position[1], self.safe_travel_z]

    async def _move_to(self, target: list[float], completion_trigger: Trigger) -> None:
        await self._run_motion(
            lambda: self.robot.move_to(target, speed=self.motion_speed), target, completion_trigger
        )

    @on_enter_state(States.pick_place.homing_traversing)
    @auto_timeout(20.0, Triggers.to_fault)
    def enter_homing_traversing(self, _):
        logger.info("Entering homing_traversing")
        target = [self.robot.home_position[0], self.robot.home_position[1], self.safe_travel_z]
        self.spawn(self._move_to(target, Triggers.finished_homing_traversing))

    @on_enter_state(States.pick_place.homing_lowering)
    @auto_timeout(10.0, Triggers.to_fault)
    def enter_homing_lowering(self, _):
        logger.info("Entering homing_lowering")
        self.spawn(
            self._run_motion(
                lambda: self.robot.move_home(speed=self.motion_speed),
                self.robot.home_position,
                Triggers.finished_homing_lowering,
            )
        )

    async def _run_motion(
        self,
        step: Callable[[], tuple[list[float], list[float], str | None]],
        target: list[float],
        completion_trigger: Trigger,
    ) -> None:
        try:
            while True:
                position, _, error = step()
                logger.debug("Current position: %s", [round(coordinate) for coordinate in position])
                if error:
                    self.last_error = error
                    self.trigger(Triggers.to_fault.name)
                    return

                if self.on_motion_update:
                    self.on_motion_update()

                if all(abs(actual - expected) < 1e-6 for actual, expected in zip(position, target)):
                    self.trigger(completion_trigger.name)
                    return

                await asyncio.sleep(self.motion_poll_interval)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self.last_error = str(error)
            self.trigger(Triggers.to_fault.name)

    @on_enter_state(States.pick_place.moving_to_cube_lifting)
    @auto_timeout(20.0, Triggers.to_fault)
    def enter_moving_to_cube_lifting(self, _):
        logger.info("Entering moving_to_cube_lifting")
        self.spawn(self._move_to(self._current_xy_at_safe_z(), Triggers.finished_moving_to_cube_lifting))

    @on_enter_state(States.pick_place.moving_to_cube_traversing)
    @auto_timeout(20.0, Triggers.to_fault)
    def enter_moving_to_cube_traversing(self, _):
        logger.info("Entering moving_to_cube_traversing")
        target = [self.cube_position[0], self.cube_position[1], self.safe_travel_z]
        self.spawn(self._move_to(target, Triggers.finished_moving_to_cube_traversing))

    @on_enter_state(States.pick_place.moving_to_cube_lowering)
    @auto_timeout(20.0, Triggers.to_fault)
    def enter_moving_to_cube_lowering(self, _):
        logger.info("Entering moving_to_cube_lowering")
        target = [self.cube_position[0], self.cube_position[1], self.cube_position[2]]
        self.spawn(self._move_to(target, Triggers.finished_moving_to_cube_lowering))

    @on_enter_state(States.pick_place.gripping)
    def enter_gripping(self, _):
        logger.info("Entering gripping")
        self.robot.closed_gripper()
        self.trigger(Triggers.finished_gripping.name)
        
    @on_enter_state(States.pick_place.moving_to_destination_lifting)
    @auto_timeout(20.0, Triggers.to_fault)
    def enter_moving_to_destination_lifting(self, _):
        logger.info("Entering moving_to_destination_lifting")
        self.spawn(self._move_to(self._current_xy_at_safe_z(), Triggers.finished_moving_to_destination_lifting))

    @on_enter_state(States.pick_place.moving_to_destination_traversing)
    @auto_timeout(30.0, Triggers.to_fault)
    def enter_moving_to_destination_traversing(self, _):
        logger.info("Entering moving_to_destination_traversing")
        target = [self.destination_position[0], self.destination_position[1], self.safe_travel_z]
        self.spawn(self._move_to(target, Triggers.finished_moving_to_destination_traversing))

    @on_enter_state(States.pick_place.moving_to_destination_lowering)
    @auto_timeout(20.0, Triggers.to_fault)
    def enter_moving_to_destination_lowering(self, _):
        logger.info("Entering moving_to_destination_lowering")
        target = [self.destination_position[0], self.destination_position[1], self.destination_position[2]]
        self.spawn(self._move_to(target, Triggers.finished_moving_to_destination_lowering))

    @on_enter_state(States.pick_place.releasing)
    def enter_releasing(self, _):
        logger.info("Entering releasing")
        self.robot.open_gripper()
        self.trigger(Triggers.finished_releasing.name)

    @on_enter_state(States.pick_place.lifting_after_release)
    @auto_timeout(10.0, Triggers.to_fault)
    def enter_lifting_after_release(self, _):
        logger.info("Entering lifting_after_release")
        target = [self.destination_position[0], self.destination_position[1], self.safe_travel_z]
        self.spawn(self._move_to(target, Triggers.finished_lifting_after_release))
