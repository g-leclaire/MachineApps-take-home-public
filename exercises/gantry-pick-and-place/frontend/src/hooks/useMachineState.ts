import { useEffect, useState } from 'react'

import { gantryClient } from '../lib/gantry-client'

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'An unexpected request error occurred.'
}

export function useMachineState(pollIntervalMs = 750) {
  const [machineState, setMachineState] = useState<string | null>(null)
  const [connectionError, setConnectionError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    let requestPending = false

    const refreshState = async () => {
      if (requestPending) return
      requestPending = true

      try {
        const response = await gantryClient.getState()
        if (active) {
          setMachineState(response.state)
          setConnectionError(null)
        }
      } catch (error: unknown) {
        if (active) setConnectionError(errorMessage(error))
      } finally {
        requestPending = false
      }
    }

    void refreshState()
    const intervalId = window.setInterval(() => void refreshState(), pollIntervalMs)

    return () => {
      active = false
      window.clearInterval(intervalId)
    }
  }, [pollIntervalMs])

  return { machineState, connectionError }
}