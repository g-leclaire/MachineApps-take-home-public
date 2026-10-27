import { useState } from 'react'

import { useMachineState } from '../hooks/useMachineState'
import { gantryClient } from '../rpc/gantry-client'
import './Dashboard.css'

function stateLabel(state: string | null): string {
  if (!state) return 'Waiting for backend'
  return state.replace(/^PickPlace_/, '').replaceAll('_', ' ')
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'An unexpected request error occurred.'
}

function Dashboard() {
  const { machineState, machineError, connectionError } = useMachineState()
  const [actionError, setActionError] = useState<string | null>(null)
  const [isStarting, setIsStarting] = useState(false)

  const startSequence = async () => {
    setIsStarting(true)
    setActionError(null)

    try {
      await gantryClient.startSequence()
      setActionError(null)
    } catch (error: unknown) {
      setActionError(errorMessage(error))
    } finally {
      setIsStarting(false)
    }
  }

  const connectionStatus = connectionError ? 'Offline' : machineState ? 'Connected' : 'Connecting'
  const isFault = machineState === 'fault'

  return (
    <main className="dashboard-shell">
      <header className="topbar">
        <p className="wordmark">GANTRY <span>/</span> PICK &amp; PLACE</p>
        <p className={`connection-status ${connectionError ? 'is-offline' : ''}`}>
          <span aria-hidden="true" />
          {connectionStatus}
        </p>
      </header>

      <section className="dashboard-content" aria-labelledby="page-title">
        <div className="page-heading">
          <p className="eyebrow">MACHINE CONTROL</p>
          <h1 id="page-title">Pick-and-place</h1>
        </div>

        <div className="control-grid">
          <section className={`state-panel ${isFault ? 'is-fault' : ''}`} aria-live="polite">
            <p className="eyebrow">CURRENT STATE</p>
            <p className="state-value">{stateLabel(machineState)}</p>
          </section>

          <section className="sequence-panel" aria-label="Sequence controls">
            <p className="eyebrow">SEQUENCE</p>
            <button
              className="start-button"
              type="button"
              onClick={() => void startSequence()}
              disabled={machineState !== 'ready' || isStarting || connectionError !== null}
            >
              <span className="play-icon" aria-hidden="true" />
              {isStarting ? 'Starting…' : 'Start sequence'}
            </button>
          </section>
        </div>

        {(connectionError || machineError || actionError) && (
          <p className="error-message" role="alert">
            {connectionError
              ? `Backend unavailable: ${connectionError}`
              : machineError
                ? `Fault: ${machineError}`
                : actionError}
          </p>
        )}
      </section>
    </main>
  )
}

export default Dashboard