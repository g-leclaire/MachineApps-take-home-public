from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import asyncio

from fastapi import FastAPI
from pydantic import BaseModel
from communication.app import VentionApp
from communication.decorators import stream
from state_machine.vention_communication import build_state_machine_rpc_bundle

from robot_control import GantryMachine


class MachineStatus(BaseModel):
    state: str
    error: str | None = None


state_machine = GantryMachine()


@stream(name="MachineStatusStream", payload=MachineStatus)
async def publish_status(state: str, error: str | None) -> MachineStatus:
    return MachineStatus(state=state, error=error)


def _on_state_change(_old_state: str, new_state: str, _trigger: str) -> None:
    error = (state_machine.last_error or "Unknown fault") if new_state == "fault" else None
    asyncio.get_running_loop().create_task(publish_status(new_state, error))


state_machine.add_state_change_callback(_on_state_change)


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
        triggers=["home", "begin_sequence", "reset"],
    )
)


app.finalize()