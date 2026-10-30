import { useState } from 'react'

import { gantryClient } from '../rpc/gantry-client'
import './RobotControls.css'

type ControlAction = 'start' | 'home'

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'An unexpected request error occurred.'
}

interface RobotControlsProps {
  machineState: string | null
  connected: boolean
}

function RobotControls({ machineState, connected }: RobotControlsProps) {
  const [error, setError] = useState<string | null>(null)
  const [pendingAction, setPendingAction] = useState<ControlAction | null>(null)

  const run = async (action: ControlAction, request: () => Promise<unknown>) => {
    setPendingAction(action)
    setError(null)

    try {
      await request()
    } catch (caught: unknown) {
      setError(errorMessage(caught))
    } finally {
      setPendingAction(null)
    }
  }

  const isReady = connected && machineState === 'ready'
  const canHome = connected && (machineState === 'ready' || machineState === 'fault')
  const busy = pendingAction !== null

  return (
    <section className="sequence-panel" aria-label="Robot controls">
      <p className="eyebrow">CONTROLS</p>
      <div className="control-buttons">
        <button
          className="start-button"
          type="button"
          onClick={() => void run('start', gantryClient.startSequence)}
          disabled={!isReady || busy}
        >
          <span className="play-icon" aria-hidden="true" />
          {pendingAction === 'start' ? 'Starting…' : 'Start sequence'}
        </button>
        <button
          className="start-button is-secondary"
          type="button"
          onClick={() => void run('home', gantryClient.home)}
          disabled={!canHome || busy}
        >
          {pendingAction === 'home' ? 'Homing…' : 'Home'}
        </button>
      </div>
      {error && (
        <p className="error-message" role="alert">
          {error}
        </p>
      )}
    </section>
  )
}

export default RobotControls
