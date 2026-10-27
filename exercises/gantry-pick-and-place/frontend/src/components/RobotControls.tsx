import { useState } from 'react'

import { gantryClient } from '../rpc/gantry-client'
import './RobotControls.css'

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'An unexpected request error occurred.'
}

interface RobotControlsProps {
  canStart: boolean
}

function RobotControls({ canStart }: RobotControlsProps) {
  const [error, setError] = useState<string | null>(null)
  const [isStarting, setIsStarting] = useState(false)

  const startSequence = async () => {
    setIsStarting(true)
    setError(null)

    try {
      await gantryClient.startSequence()
    } catch (caught: unknown) {
      setError(errorMessage(caught))
    } finally {
      setIsStarting(false)
    }
  }

  return (
    <section className="sequence-panel" aria-label="Sequence controls">
      <p className="eyebrow">SEQUENCE</p>
      <button
        className="start-button"
        type="button"
        onClick={() => void startSequence()}
        disabled={!canStart || isStarting}
      >
        <span className="play-icon" aria-hidden="true" />
        {isStarting ? 'Starting…' : 'Start sequence'}
      </button>
      {error && (
        <p className="error-message" role="alert">
          {error}
        </p>
      )}
    </section>
  )
}

export default RobotControls
