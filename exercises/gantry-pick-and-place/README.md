# **Robot Pick & Place Simulation**

## **Problem Statement**

You are tasked with building a proof-of-concept for a 3-axis gantry robot solution. The goal is to implement a Python backend that controls a robotic arm using a State Machine and a React frontend to visualize and configure the operation.

You must simulate a "Pick and Place" sequence: picking a cube from **Table A** and placing it on **Table B** within the provided application footprint.

![image](https://github.com/VentionCoExperiments/MachineApps-take-home-public/raw/main/exercises/gantry-pick-and-place/figure1_application_footprint.png)

## **Checklist of Requirements**

### **Mandatory Requirements**

**Backend (Python & FastAPI)**

  - [X] **Communication Framework:** Use the [`vention-communication`](https://pypi.org/project/vention-communication/) library to establish communication between the frontend and backend.
  - [X] **State Machine Integration:** Implement the robot's control logic using the [`vention-state-machine`](https://pypi.org/project/vention-state-machine/) library.
  - [X] **Robot Simulation:** Interface with the provided `robot_sim.py` class.
      - *Note:* The `move_to` method must be called repeatedly until motion is complete. This should be handled inside your state machine callbacks.
  - [X] **API Endpoints:** Create endpoints to:
      - Get/Set robot, cube, and destination positions.
      - specific commands: `Home Robot`, `Start Sequence`, `Get Status`.
      - *Note:* The "Home" operation moves the robot to its home position (default: `[0, 0, 0]`). Review `robot_sim.py` to understand the `move_home()` method and the `home_position` parameter.
  - [X] **Logic:** Implement the full Pick-and-Place sequence:
    1.  Move to Cube (Table A) $\rightarrow$ Lower $\rightarrow$ Close Gripper.
    2.  Lift $\rightarrow$ Move to Destination (Table B).
    3.  Lower $\rightarrow$ Open Gripper $\rightarrow$ Lift.

**Frontend (React & TypeScript)**

  - [X] **Dashboard:** Display real-time telemetry:
      - Current Robot Position (X, Y, Z).
      - Cube Start Position & Destination.
      - Robot Status (Gripper open/closed, moving/idle).
      - Current State of the State Machine.
  - [X] **Controls:** Allow the user to:
      - Configure the Cube's start coordinates and destination coordinates.
      - Trigger the "Home" operation (moves robot to home position, default: `[0, 0, 0]`).
      - Start the "Pick and Place" sequence.
  - [X] **Visuals:** Provide a clear visual indication of errors and operational state.

### **Bonus Points**

  - [X] **Persistence:** Use [`vention-storage`](https://pypi.org/project/vention-storage/) to save configuration (e.g., cube locations) between restarts.
  - [ ] **Testing:** Write unit tests for the backend logic or component tests for the frontend.
  - [X] **Containerization:** Run the whole stack (Backend + Frontend) with a single command (e.g., Docker Compose).
  - [X] **Demo:** Include a short video recording of your solution in action.

## **Run the Application**

### **Prerequisites**

- Python 3.10 (the Vention packages require Python `>=3.10,<3.11`).
- Node.js 22 and npm for the frontend.
- Docker Compose v2, if running the containerized stack.

### **Run locally**

Start the backend in one terminal:

```bash
cd backend
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Start the frontend in another terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open `http://localhost:5173`. The Vite development server proxies `/rpc` to `http://127.0.0.1:8000` by default. To use a different backend address, set `RPC_BACKEND_URL` before starting Vite.

The backend uses `sqlite:///./gantry.db` by default. Set `GANTRY_DATABASE_URL` to change the database URL. Saved cube and destination positions are loaded at startup and written when updated.

### **Run with Docker Compose**

From this directory, run:

```bash
docker compose up --build
```

Open `http://localhost:5173`; the backend is available at `http://localhost:8000`. Compose stores the SQLite database in the `gantry-data` named volume, so target positions survive container restarts. Stop the stack with `Ctrl+C` and `docker compose down`.

## **Implementation Notes**

### **Communication and controls**

The backend is a `VentionApp` exposing Connect RPC, not plain REST routes. Its service is defined in `backend/proto/app.proto`, and the TypeScript client is generated with Buf. The dashboard uses the telemetry stream for live position, gripper, motion, and state updates. RPC actions read and update robot and target positions; the state-machine RPC bundle provides the Home and Start Sequence commands.

Targets can only be edited while the machine is ready. The simulated robot position can be set directly while ready and idle (not included in dashboard). Starting a sequence or homing while the state machine is in an incompatible state is rejected by the state-machine transitions.

If the protocol changes, regenerate the frontend client from the repository root with:

```bash
cd frontend
npm run generate
```

### **State machine and motion**

`GantryMachine` uses the Vention state-machine library. Pick-and-place motion is split into explicit states: lift to safe height, traverse to the cube, lower, grip, lift, traverse to the destination, lower, release, and lift away. Each motion state starts a background coroutine from its synchronous state-entry callback. The coroutine repeatedly calls the simulator until it reaches its target, checks returned errors, and advances through an internal completion trigger. Per-state timeouts and simulator errors move the machine to `fault`; Home is allowed from `ready` or `fault` and returns the robot to its configured home position.

Only Home and Start Sequence are exposed as state-machine triggers over RPC; motion-completion triggers remain internal. Fault handling cancels spawned motion tasks and clears simulator axis speed so a later recovery move does not inherit stale motion. The database persists target positions only; robot position, gripper state, and machine state reset when the backend restarts.

### **Validation**

Build the frontend and run its lint and TypeScript checks with:

```bash
cd frontend
npm run build
```

There is currently no automated backend test suite in the repository. Starting the backend with the local command above checks that the application initializes and serves the RPC interface.

## **Design decisions, assumptions, and trade-offs**

- Backend design: The implementation is split across distinct cohesive modules (`api`, `persistence`, and `robot_control`). Module interaction is kept to a minimum to reduce coupling. `main.py` starts the server and wires the modules together.
- The gantry moves in the X/Y plane at a safe Z height to avoid collisions. 300 was chosen as the safe travel height.
  - Each movement includes lifting and lowering phases, modeled as separate states. This adds states and some repetition, but makes the robot's operation more transparent and helps identify which step failed.
  - During homing, the robot first moves to the safe travel height and traverses above its home position. It then calls `move_home()` to lower to the home position; calling it before those steps could cause a collision.
- Assumption: Treat `robot_sim.py` as an external dependency and leave it unchanged. Use its methods and constructor rather than setting its attributes directly.
  - Exception: axis speed is reset on `fault` because the simulator provides no method to stop the robot.
- The `ready` entry handler clears `last_error` so a recovered machine does not report a stale fault. The `fault` entry handler clears timeouts, cancels spawned motion tasks, and resets axis speed. This cleanup is synchronous because the state-machine library does not await its asynchronous `cancel_tasks` callback.
- A single stream carries all telemetry, including the current state.
  - This simplifies implementation and use, but clients cannot subscribe to only one type of telemetry, such as the current state or robot position.
  - Telemetry is published on each motion-loop poll (currently every 100 ms) and on each state change, but only when the snapshot changes. As a result, idle periods produce no updates, while motion produces updates at roughly 10 Hz.
- A single get/set action handles both the cube and destination positions.
  - This simplifies implementation and use, but the two positions cannot be updated independently.
  - To reduce collision risk, the positions can be changed only while the machine is `ready`. The UI also prevents submission until a value changes, avoiding unnecessary RPC calls.
  - Additional validation could check whether the new coordinates would cause the robot to collide with the cube or tables.
- The backend exposes an RPC action to set the robot position, but the UI does not provide this control, in keeping with the specification.