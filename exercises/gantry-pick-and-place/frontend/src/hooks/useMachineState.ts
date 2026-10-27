import { useEffect, useState } from 'react'

import { gantryClient } from '../rpc/gantry-client'

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'An unexpected request error occurred.'
}

export function useMachineState(reconnectDelayMs = 1000) {
  const [machineState, setMachineState] = useState<string | null>(null)
  const [machineError, setMachineError] = useState<string | null>(null)
  const [connectionError, setConnectionError] = useState<string | null>(null)

  useEffect(() => {
    const abortController = new AbortController()
    const { signal } = abortController

    const subscribe = async () => {
      while (!signal.aborted) {
        try {
          for await (const status of gantryClient.machineStatusStream(signal)) {
            setMachineState(status.state)
            setMachineError(status.error === '' ? null : status.error)
            setConnectionError(null)
          }
        } catch (error: unknown) {
          if (signal.aborted) return
          setConnectionError(errorMessage(error))
        }

        if (signal.aborted) return
        await new Promise((resolve) => window.setTimeout(resolve, reconnectDelayMs))
      }
    }

    void subscribe()

    return () => abortController.abort()
  }, [reconnectDelayMs])

  return { machineState, machineError, connectionError }
}
