import { useEffect, useState } from 'react'

import { gantryClient } from './gantryClient'
import './TargetPositions.css'

type Coordinates = [string, string, string]

const AXES = ['X', 'Y', 'Z'] as const

function toFields(position: readonly number[]): Coordinates {
  return [String(position[0] ?? ''), String(position[1] ?? ''), String(position[2] ?? '')]
}

function toNumbers(fields: Coordinates): number[] | null {
  const values = fields.map((field) => (field.trim() === '' ? NaN : Number(field)))
  return values.every(Number.isFinite) ? values : null
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'An unexpected request error occurred.'
}

interface CoordinateRowProps {
  label: string
  fields: Coordinates
  disabled: boolean
  onChange: (fields: Coordinates) => void
}

function CoordinateRow({ label, fields, disabled, onChange }: CoordinateRowProps) {
  return (
    <fieldset className="target-row">
      <legend className="eyebrow">{label}</legend>
      {AXES.map((axis, index) => (
        <label key={axis}>
          {axis}
          <input
            type="number"
            step="any"
            min={-1000}
            max={1000}
            required
            value={fields[index]}
            disabled={disabled}
            onChange={(event) => {
              const next: Coordinates = [...fields]
              next[index] = event.target.value
              onChange(next)
            }}
          />
        </label>
      ))}
    </fieldset>
  )
}

interface TargetPositionsProps {
  canEdit: boolean
}

function TargetPositions({ canEdit }: TargetPositionsProps) {
  const [cube, setCube] = useState<Coordinates>(['', '', ''])
  const [destination, setDestination] = useState<Coordinates>(['', '', ''])
  const [saved, setSaved] = useState<{ cube: Coordinates; destination: Coordinates } | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loaded = saved !== null

  useEffect(() => {
    if (loaded) return
    let active = true

    gantryClient
      .getTargetPositions()
      .then((positions) => {
        if (!active) return
        const cubeFields = toFields(positions.cubePosition)
        const destinationFields = toFields(positions.destinationPosition)
        setCube(cubeFields)
        setDestination(destinationFields)
        setSaved({ cube: cubeFields, destination: destinationFields })
      })
      .catch(() => {
        // Retried when the backend becomes editable again.
      })

    return () => {
      active = false
    }
  }, [loaded, canEdit])

  const save = async (event: React.SyntheticEvent<HTMLFormElement>) => {
    event.preventDefault()
    const cubeValues = toNumbers(cube)
    const destinationValues = toNumbers(destination)
    if (!cubeValues || !destinationValues) {
      setError('Enter a number for every coordinate.')
      return
    }

    setIsSaving(true)
    setError(null)
    try {
      const result = await gantryClient.setTargetPositions(cubeValues, destinationValues)
      const cubeFields = toFields(result.cubePosition)
      const destinationFields = toFields(result.destinationPosition)
      setCube(cubeFields)
      setDestination(destinationFields)
      setSaved({ cube: cubeFields, destination: destinationFields })
    } catch (caught: unknown) {
      setError(errorMessage(caught))
    } finally {
      setIsSaving(false)
    }
  }

  const disabled = !canEdit || isSaving
  const hasChanges =
    saved !== null &&
    (cube.some((value, index) => value !== saved.cube[index]) ||
      destination.some((value, index) => value !== saved.destination[index]))

  return (
    <section className="target-panel" aria-label="Target positions">
      <p className="eyebrow">TARGET POSITIONS</p>
      <form className="target-form" onSubmit={(event) => void save(event)}>
        <CoordinateRow label="Cube start" fields={cube} disabled={disabled} onChange={setCube} />
        <CoordinateRow label="Destination" fields={destination} disabled={disabled} onChange={setDestination} />
        <div>
          <button className="start-button" type="submit" disabled={disabled || !hasChanges}>
            {isSaving ? 'Saving…' : 'Save positions'}
          </button>
        </div>
      </form>
      {error && (
        <p className="error-message" role="alert">
          {error}
        </p>
      )}
    </section>
  )
}

export default TargetPositions
