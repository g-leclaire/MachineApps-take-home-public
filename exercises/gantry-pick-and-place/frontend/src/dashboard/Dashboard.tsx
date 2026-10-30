import { useTelemetry } from './useTelemetry'
import RobotControls from './RobotControls'
import TargetPositions from './TargetPositions'
import './Dashboard.css'

function stateLabel(state: string | null): string {
  if (!state) return 'Waiting for backend'
  return state.replace(/^PickPlace_/, '')
}

function formatPosition(position: readonly number[] | undefined): string {
  if (!position || position.length < 3) return '—'
  return position.map((value) => value.toFixed(1)).join(', ')
}

export function Dashboard() {
  const { telemetry, connectionError } = useTelemetry()
  const machineState = telemetry?.state ?? null
  const machineError = telemetry?.error ? telemetry.error : null

  const connectionStatus = connectionError ? 'Offline' : machineState ? 'Connected' : 'Connecting'
  const isFault = machineState === 'fault'

  return (
    <main className="dashboard-shell">
      <header className="topbar">
        <h1 className="wordmark" id="page-title">GANTRY PICK &amp; PLACE</h1>
        <p className={`connection-status ${connectionError ? 'is-offline' : ''}`}>
          <span aria-hidden="true" />
          {connectionStatus}
        </p>
      </header>

      <section className="dashboard-content" aria-labelledby="page-title">
        <div className="control-grid">
          <section className={`state-panel ${isFault ? 'is-fault' : ''}`} aria-live="polite">
            <p className="eyebrow">CURRENT STATE</p>
            <p className="state-value">{stateLabel(machineState)}</p>
          </section>

          <RobotControls machineState={machineState} connected={connectionError === null} />
        </div>

        <dl className="telemetry-grid" aria-label="Telemetry">
          <div>
            <dt className="eyebrow">ROBOT POSITION (X, Y, Z)</dt>
            <dd>{formatPosition(telemetry?.position)}</dd>
          </div>
          <div>
            <dt className="eyebrow">GRIPPER</dt>
            <dd>{telemetry ? (telemetry.gripperClosed ? 'Closed' : 'Open') : '—'}</dd>
          </div>
          <div>
            <dt className="eyebrow">MOTION</dt>
            <dd>{telemetry ? (telemetry.moving ? 'Moving' : 'Idle') : '—'}</dd>
          </div>
        </dl>

        <TargetPositions canEdit={machineState === 'ready' && connectionError === null} />

        {(connectionError || machineError) && (
          <p className="error-message" role="alert">
            {connectionError ? `Backend unavailable: ${connectionError}` : `Fault: ${machineError}`}
          </p>
        )}
      </section>
    </main>
  )
}