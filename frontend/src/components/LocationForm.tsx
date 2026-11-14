import { useState, type FormEvent } from 'react'

export interface FarmLocation {
  label: string
  latitude: number
  longitude: number
}

interface LocationFormProps {
  onSubmit: (location: FarmLocation) => void
}

function LocationForm({ onSubmit }: LocationFormProps) {
  const [label, setLabel] = useState('Madurai demonstration point')
  const [latitude, setLatitude] = useState('9.9252')
  const [longitude, setLongitude] = useState('78.1198')
  const [error, setError] = useState<string | null>(null)

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmedLabel = label.trim()
    const trimmedLatitude = latitude.trim()
    const trimmedLongitude = longitude.trim()

    if (!trimmedLabel || !trimmedLatitude || !trimmedLongitude) {
      setError('Enter a label, latitude, and longitude.')
      return
    }

    const parsedLatitude = Number(trimmedLatitude)
    const parsedLongitude = Number(trimmedLongitude)
    if (
      !Number.isFinite(parsedLatitude)
      || parsedLatitude < -90
      || parsedLatitude > 90
    ) {
      setError('Latitude must be a number from -90 to 90.')
      return
    }
    if (
      !Number.isFinite(parsedLongitude)
      || parsedLongitude < -180
      || parsedLongitude > 180
    ) {
      setError('Longitude must be a number from -180 to 180.')
      return
    }

    setError(null)
    onSubmit({
      label: trimmedLabel,
      latitude: parsedLatitude,
      longitude: parsedLongitude,
    })
  }

  return (
    <form className="location-form" onSubmit={handleSubmit}>
      <label className="field field-wide">
        <span>Location label</span>
        <input
          value={label}
          onChange={(event) => setLabel(event.target.value)}
          placeholder="For example, Madurai demo point"
          autoComplete="off"
          required
        />
      </label>
      <label className="field">
        <span>Latitude</span>
        <input
          type="number"
          min="-90"
          max="90"
          step="any"
          value={latitude}
          onChange={(event) => setLatitude(event.target.value)}
          required
        />
      </label>
      <label className="field">
        <span>Longitude</span>
        <input
          type="number"
          min="-180"
          max="180"
          step="any"
          value={longitude}
          onChange={(event) => setLongitude(event.target.value)}
          required
        />
      </label>
      <div className="location-submit">
        <button className="button button-primary" type="submit">Use this point</button>
      </div>
      {error && <p className="form-error" role="alert">{error}</p>}
      <p className="field-note">
        The prefilled coordinates are a demonstration point only. Enter coordinates
        you choose; no farm geometry or physical conditions are inferred.
      </p>
    </form>
  )
}

export default LocationForm
