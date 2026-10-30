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

- The gantry robot should always move on the X/Y plane from a safe Z value (height) to avoid running into objects. An arbitrary safe Z value of 300 was chosen.
  - Every movement needs a liftig and lowering phase. This was implemented by using separate states for each part of the movement. Trade-off: there is many different states for a simple operation, there can be some repetition in the state definition and implementation. However, the robot operation is more transparent. If an error occurs, it is easier to know what went wrong because the states are more specific.
  - The provided `move_home` cannot be used directly without `move_to` because it could cause the robot to run into objects.
- `robot_sim.py` should be considered as external and it should not be changed. Attributes should not be set directly. Methods and constructor should be used instead.
  - Exception: axis speed is reset on `fault` since the interface doesn't provide a way to stop the robot.
- The `ready` entry handler clears `last_error` so a recovered machine does not continue reporting a stale fault. The `fault` entry handler clears timeouts, cancels spawned motion tasks, and resets axis speed. This cleanup is performed synchronously because the state-machine library does not await its async `cancel_tasks` callback.
- A single stream was used for all telemetry including current state.
  - This makes the implementation and usage simpler. The trade-off is not being able to subscribe to a specific stream like current state or robot position.
  - Telemetry is published from the motion loop on every poll (currently every 100 ms) and on every state change, but only when the snapshot differs from the last one published, so idle periods send nothing and the stream stays at roughly 10 Hz while moving.
- A single get/set was used for cube and destination positions.
  - This makes the implementation, usage and user experience simpler. The trade-off is that cube position and destination cannot be set individually.
  - To prevent problems like running into objects, the cube and destination positions can only be set when the state is `ready`. The UI also prevents the user from submitting values if they haven't changed to prevent backend calls.
  - To go a step further, we should validate that the robot doesn't clip the cube or tables with the new coordinates.
- The robot position can be set from the backend endpoint, but not through the UI. This follows the specifications.