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
- `reset` is only defined from `fault` to `ready`, not globally. A `Trigger("reset").transition("*", "ready")` of our own works from any state.
- `to_fault` does not cancel spawned tasks (its `cancel_tasks` callback is async and never awaited), and `reset` does not either. Tasks keep running unless we cancel `state_machine._tasks` ourselves. Verified workaround: a sync `@on_enter_state("fault")` handler and a `before` callback on the reset transition.
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

Triggers: `home`, `begin_sequence`, a distinct `finished_*` trigger for each motion and gripper state, plus built-in `to_fault` and `reset`. Completion triggers are internal and must never be callable from the frontend.

- [x] Transitions: `home`: `ready -> homing -> ready`; sequence: `ready -> moving_to_cube -> lowering_at_cube -> gripping -> lifting_with_cube -> moving_to_destination -> lowering_at_destination -> releasing -> lifting_after_release -> ready`, with `begin_sequence` starting it and every step completed by its matching `finished_*` trigger. `to_fault` remains available from any state; `reset` returns to `ready` from any state.
- [x] Define states, triggers and transitions, including a `start` self-transition on `ready` so `await state_machine.start()` can fire successfully. Add `Trigger("reset").transition("*", "ready")` since the library's `reset` is only from `fault`.
- [ ] Guards: define `begin_sequence` and `home` only from `ready`; the transition table is the guard, so no `@guard` is needed. Invalid triggers come back as `failed_precondition` over RPC.
- [ ] On `fault` and on `reset`: cancel all tasks in `state_machine._tasks` ourselves (a sync `@on_enter_state("fault")` handler, and a `before` callback on the reset transition).
- [ ] On `reset`: stop residual motion and open the gripper using the simulator API in [AGENTS.md](AGENTS.md); clear `last_error`.
- [ ] Motion helper: a sync `@on_enter_state` callback spawns a coroutine that repeatedly calls `robot.move_to(...)` with a short `asyncio.sleep`, checks the simulator's result/error per [AGENTS.md](AGENTS.md), and fires the matching `finished_*` trigger when the target is reached.
- [ ] Gripper states: sync entry callbacks perform the gripper action, then schedule the matching internal one-shot `finished_gripping` or `finished_releasing` trigger (for example with `self.spawn(...)`) so the sequence advances without waiting for a motion loop.
- [ ] Wrap the motion coroutine in try/except so unexpected exceptions store `last_error` and fire `to_fault`; handle returned simulator errors as specified in [AGENTS.md](AGENTS.md).
- [ ] Validate simulator inputs at the API boundary according to [AGENTS.md](AGENTS.md).
- [x] Expose RPC with `build_state_machine_rpc_bundle(state_machine, triggers=["home", "begin_sequence", "reset"])` so all `finished_*` triggers stay internal.

### API (README: "API Endpoints")

- [ ] Pydantic models for positions, status and requests.
- [ ] Actions: get/set robot position, cube position, destination position.
- [ ] Actions: `Home Robot`, `Start Sequence`, `Get Status`.
- [ ] Validate set-position inputs at the boundary according to [AGENTS.md](AGENTS.md).
- [ ] Stream: telemetry with position, gripper state, moving/idle, cube start, destination, state machine state.
- [x] Register the state machine bundle with `app.register_rpc_plugin(...)`, then `app.finalize()` last; confirm `proto/app.proto` is emitted.

### Checks

- [ ] Server boots (`uvicorn main:app --reload`).
- [ ] Unit tests for transitions and guards (see Phase 4).

## Phase 2: Frontend (mandatory)

- [x] Scaffold Vite + React + TypeScript (strict).
- [x] Generate the client from `proto/app.proto` with Buf and `@connectrpc/connect-web`.
- [ ] Dashboard: robot X/Y/Z, cube start, destination, gripper open/closed, moving/idle, state machine state (from the stream).
- [ ] Controls: cube start and destination inputs, Home button, Start Sequence button.
- [ ] Visuals: distinct fault state and error message, reset button, clear indication of the current state.
- [x] `npm run build` and lint/type check pass.

## Phase 3: End-to-end check

- [ ] Run the full sequence from the UI and confirm each state is visited in order.
- [ ] Trigger a fault (e.g. out-of-range position), confirm the UI shows it and reset recovers.

## Phase 4: Bonus (only after Phases 1-3)

- [ ] Tests: backend state machine tests with a fake or real `Robot`; optional frontend component tests.
- [ ] Persistence: `vention-storage` for cube and destination positions across restarts.
- [ ] Containerization: Docker Compose for backend and frontend.
- [ ] Demo: short screen recording.

## Phase 5: Submission

- [ ] Root `README.md` with setup/run instructions and design decisions, assumptions and trade-offs.
- [ ] Push to the fork and share the link.

## Decisions log

Record decisions here as they are made, for the final README write-up.

- Use a distinct internal `finished_*` trigger for each motion and gripper state, following the Vention docs. Only `home`, `begin_sequence` and `reset` are exposed over RPC.
- `reset` is allowed from any state and acts as an abort: it cancels motion, clears residual motion state, and opens the gripper. Chosen so the user can stop a run. Needs our own `"*"` reset transition because the library only allows it from `fault`.
- Spawned tasks are cancelled by our own handlers on fault and reset, because the library's `to_fault` does not cancel them.
- Libraries upgraded to the latest releases (state-machine 0.16.26, communication 0.15.32, storage 0.20.10); the originally pinned versions lacked parts of the documented API.
- Startup simulation is skipped because the external simulator has no connect/enable API; construction leaves the state machine in `ready`.
- Use safe travel Z `750`, pickup `[-500, 500, 500]`, and placement `[500, -500, 500]` as configurable defaults.
- Use motion speed `100` mm/s and poll every `50` ms; report moving from non-zero simulator axis speed.
- Disallow Home and position edits during a sequence, and snapshot pickup/placement coordinates at sequence start to prevent moving targets.
- Use a single stream for all telemerty including current state, use get/set for cube and destination positions
