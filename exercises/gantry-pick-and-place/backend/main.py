from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import asyncio
import math

from fastapi import FastAPI
from pydantic import BaseModel, field_validator
from communication.app import VentionApp
from communication.decorators import action, stream
from communication.errors import ConnectError
from state_machine.vention_communication import build_state_machine_rpc_bundle

from robot_control import GantryMachine
from robot_sim import GripperState


class Telemetry(BaseModel):
    state: str
    error: str | None = None
    position: list[float]
    gripper_closed: bool
    moving: bool


def _validate_coordinates(value: list[float]) -> list[float]:
    if len(value) != 3 or not all(-1000 <= coordinate <= 1000 for coordinate in value):
        raise ValueError("Expected three coordinates within [-1000, 1000]")
    return value


class RobotPosition(BaseModel):
    position: list[float]

    @field_validator("position")
    @classmethod
    def _validate_position(cls, value: list[float]) -> list[float]:
        return _validate_coordinates(value)


class TargetPositions(BaseModel):
    cube_position: list[float]
    destination_position: list[float]

    @field_validator("cube_position", "destination_position")
    @classmethod
    def _validate_positions(cls, value: list[float]) -> list[float]:
        return _validate_coordinates(value)


state_machine = GantryMachine()
_last_telemetry: Telemetry | None = None


@stream(name="TelemetryStream", payload=Telemetry)
async def publish_telemetry(telemetry: Telemetry) -> Telemetry:
    return telemetry


def _snapshot() -> Telemetry:
    robot = state_machine.robot
    state = state_machine.state
    error = (state_machine.last_error or "Unknown fault") if state == "fault" else None
    return Telemetry(
        state=state,
        error=error,
        position=list(robot.current_position),
        gripper_closed=robot.gripper_state == GripperState.CLOSED,
        moving=any(robot.axis_speed),
    )


def _publish_if_changed(*_: object) -> None:
    global _last_telemetry
    telemetry = _snapshot()
    if telemetry == _last_telemetry:
        return
    _last_telemetry = telemetry
    asyncio.get_running_loop().create_task(publish_telemetry(telemetry))


@action()
async def get_robot_position() -> RobotPosition:
    return RobotPosition(position=list(state_machine.robot.current_position))


@action()
async def set_robot_position(position: RobotPosition) -> RobotPosition:
    robot = state_machine.robot
    if state_machine.state != "ready" or any(robot.axis_speed):
        raise ConnectError(
            code="failed_precondition",
            message=f"Robot position can only be changed while ready and idle (state: '{state_machine.state}')",
        )
    state_machine.set_robot_position(position.position)
    _publish_if_changed()
    return position


@action()
async def get_target_positions() -> TargetPositions:
    return TargetPositions(
        cube_position=state_machine.cube_position,
        destination_position=state_machine.destination_position,
    )


@action()
async def set_target_positions(positions: TargetPositions) -> TargetPositions:
    if state_machine.state != "ready":
        raise ConnectError(
            code="failed_precondition",
            message=f"Positions can only be changed while ready (state: '{state_machine.state}')",
        )
    state_machine.cube_position = list(positions.cube_position)
    state_machine.destination_position = list(positions.destination_position)
    return positions


state_machine.add_state_change_callback(_publish_if_changed)
state_machine.on_motion_update = _publish_if_changed


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    await state_machine.start()
    try:
        yield
    finally:
        await state_machine.cancel_tasks()


app = VentionApp(name="GantryPickAndPlace", emit_proto=True, lifespan=lifespan)
app.register_rpc_plugin(
    build_state_machine_rpc_bundle(
        state_machine,
        triggers=["home", "begin_sequence"],
    )
)


app.finalize()