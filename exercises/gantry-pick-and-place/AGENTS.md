# Agent Instructions

3-axis gantry pick-and-place take-home. Python backend (FastAPI + Vention libraries) and React/TypeScript frontend. The requirements are in [README.md](README.md); treat it as the source of truth and do not re-interpret it or change it.

## Layout

- `backend/`: Python backend. `robot_sim.py` is an externally provided simulator; treat it as an immutable dependency and do not change it.
- `frontend/`: React + TypeScript (Vite). Created by us; does not exist yet.
- Vention reference docs and source are installed under `backend/venv/lib/python3.10/site-packages/`.

## Library docs (read first)

The Vention libraries are small and not well known. Never guess their APIs. Read the installed `METADATA` docs and inspect package source before using an API.

- State machine docs: [vention-state-machine METADATA](backend/venv/lib/python3.10/site-packages/vention_state_machine-0.16.26.dist-info/METADATA); source: `backend/venv/lib/python3.10/site-packages/state_machine/`.
- Communication/RPC docs: [vention-communication METADATA](backend/venv/lib/python3.10/site-packages/vention_communication-0.15.32.dist-info/METADATA); source: `backend/venv/lib/python3.10/site-packages/communication/`.
- Storage docs: [vention-storage METADATA](backend/venv/lib/python3.10/site-packages/vention_storage-0.20.10.dist-info/METADATA); source: `backend/venv/lib/python3.10/site-packages/storage/`.

If metadata docs and installed source disagree, installed source wins. Report the discrepancy.

## Backend rules

- Python 3.10 only (the Vention libraries require `>=3.10,<3.11`), async FastAPI. Run from `backend/` with the venv active: `uvicorn main:app --reload`.
- Pinned versions are in `backend/requirements.txt`. Do not upgrade or add dependencies without asking.
- Expose the backend to the frontend only through `vention-communication` (`@action`, `@stream`, `VentionApp`). Do not add plain REST routes.
- Implement the control logic as a `vention-state-machine` `StateMachine` with `StateGroup`, `State` and `Trigger`. Do not hand-roll a state variable or `if/else` phase tracking.
- Register the state machine with `build_state_machine_rpc_bundle` (from `state_machine.vention_communication`, not `build_state_machine_bundle`) and `app.register_rpc_plugin(...)`, then call `app.finalize()` last. Pass `triggers=[...]` so internal triggers such as `step_done` are not exposed.
- Define a `start` transition and call `await state_machine.start()` during async startup. `@on_enter_state` callbacks must be sync; start async work from them with `self.spawn(...)`.
- `Robot.move_to(target, speed)` is synchronous and non-blocking. It advances motion based on elapsed time and returns `(position, axis_speed, error)` on every call; check `error` because invalid requests return an error string instead of raising. Call repeatedly until the position reaches the target, from a spawned async loop with a short `await asyncio.sleep`; never use a blocking loop or `time.sleep` in a state callback.
- Use `state_machine.spawn(...)` for background coroutines, and cancel `state_machine._tasks` yourself on fault and reset: the library's `to_fault` does not cancel them, and `reset` is only defined from `fault` unless you add a transition.
- The simulator checks speed against `[0, 100]` and each supplied coordinate against `[-1000, 1000]`, returning errors in the third tuple item. It does not check axis count or finite values, and speed `0` can cause division by zero for a non-zero move. Validate inputs at the API boundary (three finite coordinates in range and speed `1..100`) and route failures to the `fault` state.
- Home with `robot.move_home()`; it returns the same 3-tuple as `move_to`, despite its `bool` annotation.
- Close the gripper with the provided API name `robot.closed_gripper()` (not `close_gripper()`); `robot.open_gripper()` opens it.
- Model each step of the README's pick-and-place sequence as its own state.
- Publish telemetry through `@stream` with the defaults (`replay=True`, `queue_maxsize=1`, `policy="latest"`).
- Use Pydantic models for every request and response type.

## Frontend rules

- React + TypeScript with strict types. No `any`.
- Generate the client from the emitted `proto/app.proto` with Buf and `@connectrpc/connect-web`, as described in the communication doc. Do not hand-write fetch calls or duplicate backend types.
- Build the README's dashboard and controls, using streams for live updates.
- Create new React component as often as needed to encapsulate features. Each component should have its own CSS file when styles are needed.

## Workflow

- For a non-trivial feature, outline the states, triggers and API first, then implement.
- Work in small steps: backend first, then frontend, then bonus items.
- After backend changes, run the tests (`pytest` in `backend/`) and start the server to check it boots. After frontend changes, run `npm run build` and the lint/type check.
- Add tests for the state machine transitions and guards using a fake or real `Robot`. Test the logic, not the library.
- Keep changes minimal and focused. Do not refactor unrelated code or add features that are not in the README.

- Do the README's bonus items only after the mandatory ones work.
- When a design decision is made (state design, error handling, etc.), note it for the final write-up in the root `README.md`.
