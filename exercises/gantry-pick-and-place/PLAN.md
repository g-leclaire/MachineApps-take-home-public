# Plan

Derived from [README.md](README.md). Work top to bottom; do not start a phase until the previous one runs. Design items marked "proposal" are not in the README and can change.

## Phase 0: Setup

- [x] Create venv and install `backend/requirements.txt` (libraries upgraded to the latest releases).
- [x] Read the installed library sources and compare with `docs/` (installed source wins). See "Library findings" below.
- [x] Read the simulator contract in [AGENTS.md](AGENTS.md); treat `backend/robot_sim.py` as immutable.
- [x] Record user-approved design defaults in the Phase 1 proposal and decisions log.

### Library findings (installed source, verified by running it)

Installed: `vention-state-machine==0.16.26`, `vention-communication==0.15.32`, `vention-storage==0.20.10`. All three require Python `>=3.10,<3.11`, so the venv must stay on 3.10.

Differences from `docs/` that affect the design:

- The RPC bundle builder is `state_machine.vention_communication.build_state_machine_rpc_bundle`, not `build_state_machine_bundle`. It adds `GetState`, `GetHistory` and one `Trigger_<Name>` action per trigger (only the first letter is capitalised, e.g. `Trigger_Step_done`). `triggers=[...]` limits which ones are exposed; the others return 404.
- Invoking a trigger over RPC from the wrong state returns a Connect error envelope with code `failed_precondition` (HTTP 200 with an `error` body), not an exception.
- `await start()` is async and fires a `start` trigger, so define an explicit `start` transition and call it during async startup with `enable_last_state_recovery=False`.
- `to_fault` does not cancel spawned tasks (its `cancel_tasks` callback is async and never awaited). Tasks keep running unless we cancel `state_machine._tasks` ourselves, so fault handling uses a sync `@on_enter_state("fault")` handler.
- Firing a trigger directly in Python with no transition from the current state raises `MachineError`.
- A trigger name can be reused across several transitions (verified experimentally).
- `@on_enter_state` callbacks must be sync: an `async def` is never awaited (verified). Start async work with `self.spawn(...)` from a sync callback.
- `@stream` functions become publishers: `await publish()` publishes the function's return value, and only works after `app.finalize()`.
- `vention-storage`: the default database is `./storage.db` relative to the working directory (override with `VENTION_STORAGE_DATABASE_URL` or `bootstrap(database_url=...)`); `bootstrap()` must run after the models are imported.

## Phase 1: Backend (mandatory)

### State machine (proposal)

States (one per README step), in a `StateGroup`, plus the built-in `ready` and `fault`:

| State | Entry action |
| --- | --- |
| `homing` | move robot to its home position until motion completes |
| `moving_to_cube` | move to cube X, Y at safe Z |
| `lowering_at_cube` | move down to pick Z |
| `gripping` | close gripper |
| `lifting_with_cube` | move up to safe Z |
| `moving_to_destination` | move to destination X, Y at safe Z |
| `lowering_at_destination` | move down to place Z |
| `releasing` | open gripper |
| `lifting_after_release` | move up to safe Z |

Coordinate defaults: safe travel Z is `1000`; cube pickup position is `[-500, 500, 500]`; placement position is `[500, -500, 500]`. Treat these as configurable positions, with these initial values.

Triggers: `home`, `begin_sequence`, a distinct `finished_*` trigger for each motion and gripper state, plus built-in `to_fault`. Completion triggers are internal and must never be callable from the frontend.

- [x] Transitions: `home`: `ready` or `fault` -> `homing` -> `ready`; sequence: `ready -> moving_to_cube -> lowering_at_cube -> gripping -> lifting_with_cube -> moving_to_destination -> lowering_at_destination -> releasing -> lifting_after_release -> ready`, with `begin_sequence` starting it and each step completed by its matching `finished_*` trigger. `to_fault` remains available from any state.
- [x] Define states and triggers, including a `start` self-transition on `ready` so `await state_machine.start()` can fire successfully.
- [x] Guards: `begin_sequence` is only available from `ready`; `home` is available from `ready` and `fault`. The transition table is the guard, so no `@guard` is needed. Invalid triggers come back as `failed_precondition` over RPC.
- [x] On `fault`, cancel all tasks in `state_machine._tasks` in a sync `@on_enter_state("fault")` handler.
- [x] Motion helper: a sync `@on_enter_state` callback spawns a coroutine that repeatedly calls the simulator motion method, checks its result/error per [AGENTS.md](AGENTS.md), and fires the matching `finished_*` trigger when the target is reached.
- [x] Gripper states: sync entry callbacks perform the gripper action and fire the matching internal `finished_gripping` or `finished_releasing` trigger.
- [x] Wrap the motion coroutine in try/except so unexpected exceptions store `last_error` and fire `to_fault`; handle returned simulator errors as specified in [AGENTS.md](AGENTS.md).
- [x] Validate target coordinates at the API boundary according to [AGENTS.md](AGENTS.md).
- [x] Expose RPC with `build_state_machine_rpc_bundle(state_machine, triggers=["home", "begin_sequence"])` so all `finished_*` triggers stay internal.

### API (README: "API Endpoints")

- [x] Pydantic models for target-position requests/responses and telemetry status.
- [x] Actions: get/set robot position (editable from the dashboard while the machine is ready and idle).
- [x] Actions: get/set cube position and destination position.
- [x] Actions: `Home Robot` and `Start Sequence`; status is supplied by telemetry.
- [x] Validate set-position inputs at the boundary according to [AGENTS.md](AGENTS.md).
- [x] Stream: telemetry with robot position, gripper state, moving/idle, state machine state and fault error. Target positions are available through get/set actions.
- [x] Register the state machine bundle with `app.register_rpc_plugin(...)`, then `app.finalize()` last; confirm `proto/app.proto` is emitted.

### Checks

- [x] Server boots (`uvicorn main:app --reload`).
- [ ] Unit tests for transitions and guards (see Phase 4).

## Phase 2: Frontend (mandatory)

- [x] Scaffold Vite + React + TypeScript (strict).
- [x] Generate the client from `proto/app.proto` with Buf and `@connectrpc/connect-web`.
- [x] Dashboard: robot X/Y/Z, cube start, destination, gripper open/closed, moving/idle, and state machine state.
- [x] Controls: cube start and destination inputs, Home button, Start Sequence button.
- [x] Visuals: distinct fault state and error message, and clear indication of the current state.
- [x] `npm run build` and lint/type check pass.

## Phase 3: End-to-end check

- [X] Run the full sequence from the UI and confirm each state is visited in order.
- [X] Trigger a fault (e.g. out-of-range position), confirm the UI shows it and Home recovers.

## Phase 4: Bonus (only after Phases 1-3)

- [ ] Tests: backend state machine tests with a fake or real `Robot`; optional frontend component tests.
- [X] Persistence: `vention-storage` for cube and destination positions across restarts.
- [X] Containerization: Docker Compose for backend and frontend.
- [X] Demo: short screen recording.

## Phase 5: Submission

- [X] Root `README.md` with setup/run instructions and design decisions, assumptions and trade-offs.
- [X] Push to the fork and share the link.

## Decisions log

Record decisions here as they are made, for the final README write-up.

- Use a distinct internal `finished_*` trigger for each motion and gripper state, following the Vention docs. Only `home` and `begin_sequence` are exposed over RPC.
- Spawned tasks are cancelled by our own handler on fault, because the library's `to_fault` does not cancel them.
- Libraries upgraded to the latest releases (state-machine 0.16.26, communication 0.15.32, storage 0.20.10); the originally pinned versions lacked parts of the documented API.
- Use arbitrary safe travel Z, initial pickup, and initial placement coordinates as configurable defaults (through changing the code).
- Use motion speed `100` mm/s and poll every `100` ms; report moving from non-zero simulator axis speed.
- Disallow Home and position edits during a sequence, and snapshot pickup/placement coordinates at sequence start to prevent moving targets.
- Use a single stream for all telemerty including current state, use get/set for cube and destination positions
- Home is the recovery path: `home` is allowed from `ready` and from `fault`. A move in progress cannot be aborted; it must finish or fault by its timeout.
- Home runs through the same motion loop as the sequence, using `robot.move_home()`, in its own `homing` state with a 30 s timeout that triggers a fault. `_run_motion` takes a step callable instead of a flag, so `move_to` and `move_home` share the polling, error and completion handling.
- Fault handling is a sync `@on_enter_state("fault")` hook, not a `before` callback on a transition: callbacks passed through the transition table are never awaited by the library. The hook cancels all spawned tasks and pending timeouts, so a timeout-triggered fault cannot leave the robot still moving or fire a stale completion trigger later.
- The fault hook also zeroes `robot.axis_speed`. The simulator has no stop call and `move_to` only plans a new move when all axis speeds are zero, so a stale velocity from an interrupted move would break the next move (the later Home).
- Fault reporting: simulator errors (returned in the third tuple item) and unexpected exceptions are stored in `last_error` and fire `to_fault`; timeouts fault without a message. The telemetry `error` is only set while in `fault` (falling back to "Unknown fault") and `last_error` is cleared on entering `ready`, so an old error never carries into a later fault.
- Motion speed is a fixed constant (100 mm/s, the simulator maximum) and not user-configurable, which avoids the simulator's out-of-range and speed-0 division-by-zero cases. Cube and destination coordinates are validated at the API boundary (three values within +/-1000) and can only be changed while `ready`.
- Robot position can be set directly while the machine is ready and idle; the change is published through telemetry.
- Telemetry is published from the motion loop on every poll (currently every 100 ms) and on every state change, but only when the snapshot differs from the last one published, so idle periods send nothing and the stream stays at roughly 10 Hz while moving.
- Don't add a get state action, instead rely on telemetry