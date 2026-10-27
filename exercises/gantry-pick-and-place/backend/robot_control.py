import asyncio

from state_machine.core import StateMachine
from state_machine.defs import State, StateGroup, Trigger
from state_machine.decorators import on_enter_state, auto_timeout

from robot_sim import Robot


class PickPlace(StateGroup):
    homing = State()
    moving_to_cube = State()
    lowering_at_cube = State()
    gripping = State()
    lifting_with_cube = State()
    moving_to_destination = State()
    lowering_at_destination = State()
    releasing = State()
    lifting_after_release = State()

class States:
    pick_place = PickPlace()

class Triggers:
    start = Trigger("start")
    home = Trigger("home")
    begin_sequence = Trigger("begin_sequence")
    finished_homing = Trigger("finished_homing")
    finished_moving_to_cube = Trigger("finished_moving_to_cube")
    finished_lowering_at_cube = Trigger("finished_lowering_at_cube")
    finished_gripping = Trigger("finished_gripping")
    finished_lifting_with_cube = Trigger("finished_lifting_with_cube")
    finished_moving_to_destination = Trigger("finished_moving_to_destination")
    finished_lowering_at_destination = Trigger("finished_lowering_at_destination")
    finished_releasing = Trigger("finished_releasing")
    finished_lifting_after_release = Trigger("finished_lifting_after_release")
    to_fault = Trigger("to_fault")
    reset = Trigger("reset")

TRANSITIONS = [
    Triggers.start.transition("ready", "ready"),
    Triggers.home.transition("ready", States.pick_place.homing),
    Triggers.finished_homing.transition(States.pick_place.homing, "ready"),
    Triggers.begin_sequence.transition("ready", States.pick_place.moving_to_cube),
    Triggers.finished_moving_to_cube.transition(States.pick_place.moving_to_cube, States.pick_place.lowering_at_cube),
    Triggers.finished_lowering_at_cube.transition(States.pick_place.lowering_at_cube, States.pick_place.gripping),
    Triggers.finished_gripping.transition(States.pick_place.gripping, States.pick_place.lifting_with_cube),
    Triggers.finished_lifting_with_cube.transition(States.pick_place.lifting_with_cube, States.pick_place.moving_to_destination),
    Triggers.finished_moving_to_destination.transition(States.pick_place.moving_to_destination, States.pick_place.lowering_at_destination),
    Triggers.finished_lowering_at_destination.transition(States.pick_place.lowering_at_destination, States.pick_place.releasing),
    Triggers.finished_releasing.transition(States.pick_place.releasing, States.pick_place.lifting_after_release),
    Triggers.finished_lifting_after_release.transition(States.pick_place.lifting_after_release, "ready"),
    Triggers.reset.transition("*", "ready"),
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
        super().__init__(
            states=States,
            transitions=TRANSITIONS,
            enable_last_state_recovery=False
        )

    @on_enter_state(States.pick_place.moving_to_cube)
    @auto_timeout(20.0, Triggers.to_fault)
    def enter_moving_to_cube(self, _):
        print("Entering moving_to_cube")
        target = [self.cube_position[0], self.cube_position[1], self.safe_travel_z]
        self.spawn(self._move_to(target, Triggers.finished_moving_to_cube))

    async def _move_to(self, target: list[float], completion_trigger: Trigger) -> None:
        try:
            while True:
                position, _, error = self.robot.move_to(target, speed=self.motion_speed)
                print(f"Current position: {[round(coordinate) for coordinate in position]}")
                if error:
                    self.last_error = error
                    self.trigger(Triggers.to_fault.name)
                    return

                if all(abs(actual - expected) < 1e-6 for actual, expected in zip(position, target)):
                    self.trigger(completion_trigger.name)
                    return

                await asyncio.sleep(self.motion_poll_interval)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self.last_error = str(error)
            self.trigger(Triggers.to_fault.name)

    @on_enter_state(States.pick_place.lowering_at_cube)
    @auto_timeout(10.0, Triggers.to_fault)
    def enter_lowering_at_cube(self, _):
        print("Entering lowering_at_cube")
        target = [self.cube_position[0], self.cube_position[1], self.cube_position[2]]
        self.spawn(self._move_to(target, Triggers.finished_lowering_at_cube))

    @on_enter_state(States.pick_place.gripping)
    def enter_gripping(self, _):
        print("Entering gripping")
        self.robot.closed_gripper()
        self.trigger(Triggers.finished_gripping.name)
        
    @on_enter_state(States.pick_place.lifting_with_cube)
    @auto_timeout(10.0, Triggers.to_fault)
    def enter_lifting_with_cube(self, _):
        print("Entering lifting_with_cube")
        target = [self.cube_position[0], self.cube_position[1], self.safe_travel_z]
        self.spawn(self._move_to(target, Triggers.finished_lifting_with_cube))

    @on_enter_state(States.pick_place.moving_to_destination)
    @auto_timeout(20.0, Triggers.to_fault)
    def enter_moving_to_destination(self, _):
        print("Entering moving_to_destination")
        target = [self.destination_position[0], self.destination_position[1], self.safe_travel_z]
        self.spawn(self._move_to(target, Triggers.finished_moving_to_destination))

    @on_enter_state(States.pick_place.lowering_at_destination)
    @auto_timeout(10.0, Triggers.to_fault)
    def enter_lowering_at_destination(self, _):
        print("Entering lowering_at_destination")
        target = [self.destination_position[0], self.destination_position[1], self.destination_position[2]]
        self.spawn(self._move_to(target, Triggers.finished_lowering_at_destination))

    @on_enter_state(States.pick_place.releasing)
    def enter_releasing(self, _):
        print("Entering releasing")
        self.robot.open_gripper()
        self.trigger(Triggers.finished_releasing.name)

    @on_enter_state(States.pick_place.lifting_after_release)
    @auto_timeout(10.0, Triggers.to_fault)
    def enter_lifting_after_release(self, _):
        print("Entering lifting_after_release")
        target = [self.destination_position[0], self.destination_position[1], self.safe_travel_z]
        self.spawn(self._move_to(target, Triggers.finished_lifting_with_cube))
