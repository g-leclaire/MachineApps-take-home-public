import { useEffect, useState } from 'react'

import type { Telemetry } from '../gen/app_pb'
import { gantryClient } from './gantryClient'

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'An unexpected request error occurred.'
}

export function useTelemetry(reconnectDelayMs = 1000) {
  const [telemetry, setTelemetry] = useState<Telemetry | null>(null)
  const [connectionError, setConnectionError] = useState<string | null>(null)

  useEffect(() => {
    const abortController = new AbortController()
    const { signal } = abortController

    const subscribe = async () => {
      while (!signal.aborted) {
        try {
          for await (const update of gantryClient.telemetryStream(signal)) {
            setTelemetry(update)
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

  return { telemetry, connectionError }
}
