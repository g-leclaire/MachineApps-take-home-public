from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from communication.app import VentionApp
from state_machine.vention_communication import build_state_machine_rpc_bundle

from robot_control import GantryMachine
from robot_api import register_robot_api
from persistence import init_storage, load_target_positions, save_target_positions


state_machine = GantryMachine()
config_accessor = init_storage()
stored_targets = load_target_positions(config_accessor)
if stored_targets is not None:
    state_machine.set_target_positions(*stored_targets)
register_robot_api(
    state_machine,
    lambda cube, destination: save_target_positions(config_accessor, cube, destination),
)


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