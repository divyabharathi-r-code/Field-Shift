import { useLayoutEffect, useRef, useState, type FormEvent } from 'react'
import { explainApiError, getDailyEnvironment } from '../api'
import type { EnvironmentalResponse } from '../types'
import type { FarmLocation } from './LocationForm'

interface EnvironmentalPanelProps {
  location: FarmLocation | null
}

function EnvironmentalPanel({ location }: EnvironmentalPanelProps) {
  const [startDate, setStartDate] = useState('2020-01-01')
  const [endDate, setEndDate] = useState('2020-01-07')
  const [response, setResponse] = useState<EnvironmentalResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const requestId = useRef(0)

  useLayoutEffect(() => {
    requestId.current += 1
    setResponse(null)
    setError(null)
    setLoading(false)
  }, [location?.latitude, location?.longitude, startDate, endDate])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setResponse(null)

    if (!location) {
      setError('Set and confirm a point location before requesting NASA POWER data.')
      return
    }
    if (!startDate || !endDate || startDate > endDate) {
      setError('Choose a valid date range; the start date must not follow the end date.')
      return
    }

    const currentRequestId = ++requestId.current
    setLoading(true)
    try {
      const result = await getDailyEnvironment({
        latitude: location.latitude,
        longitude: location.longitude,
        start_date: startDate,
        end_date: endDate,
      })
      if (currentRequestId === requestId.current) setResponse(result)
    } catch (requestError) {
      if (currentRequestId === requestId.current) {
        setError(explainApiError(requestError))
      }
    } finally {
      if (currentRequestId === requestId.current) setLoading(false)
    }
  }

  const observations = response?.data.observations ?? []

  return (
    <section className="panel environment-panel" aria-labelledby="environment-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">02 — NASA POWER</p>
          <h2 id="environment-heading">Environmental context</h2>
        </div>
        <span className="badge badge-experimental">EXPERIMENTAL · GRIDDED</span>
      </div>
      <p className="section-intro">
        Request the existing daily endpoint for the active point. Returned values are
        provider-gridded context, not measurements from a farm weather station.
      </p>

      <form className="environment-controls" onSubmit={handleSubmit}>
        <label className="field">
          <span>Start date</span>
          <input
            type="date"
            value={startDate}
            onChange={(event) => setStartDate(event.target.value)}
            required
          />
        </label>
        <label className="field">
          <span>End date</span>
          <input
            type="date"
            value={endDate}
            onChange={(event) => setEndDate(event.target.value)}
            required
          />
        </label>
        <button className="button button-dark" type="submit" disabled={loading}>
          {loading ? 'Requesting…' : 'Request daily data'}
        </button>
      </form>

      {!response && !error && !loading && (
        <div className="empty-state">
          <span className="empty-icon" aria-hidden="true">↗</span>
          <p>
            {location
              ? 'No environmental data requested yet. NASA access may be disabled or unavailable.'
              : 'Confirm a point location to enable a data request.'}
          </p>
        </div>
      )}
      {loading && <p className="notice notice-info" role="status">Requesting the configured NASA POWER source…</p>}
      {error && (
        <div className="notice notice-warning" role="alert">
          <strong>Environmental data unavailable</strong>
          <p>{error}</p>
          <p>No fabricated or substitute NASA values are displayed.</p>
        </div>
      )}

      {response && (
        <div className="environment-result">
          {response.data.experimental && (
            <p className="notice notice-info">
              Experimental source · verification status: <strong>{response.data.source_verification_status}</strong>
            </p>
          )}
          {observations.length === 0 ? (
            <div className="empty-state">
              <p>The API returned no observations for this request.</p>
            </div>
          ) : (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Date (UTC)</th>
                    <th>Parameter</th>
                    <th>Value</th>
                    <th>Units</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {observations.map((observation, index) => (
                    <tr key={`${observation.date}-${observation.parameter}-${index}`}>
                      <td>{observation.date}</td>
                      <td><code>{observation.parameter}</code></td>
                      <td>{observation.value === null ? 'Missing' : observation.value}</td>
                      <td>{observation.units}</td>
                      <td>
                        <span className={`status-label ${observation.status === 'ok' ? 'status-ok' : 'status-missing'}`}>
                          {observation.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {observations.every((item) => item.value === null) && (
                <p className="field-note">All returned values are missing; none are replaced with zero.</p>
              )}
            </div>
          )}

          <div className="provenance-block">
            <div className="provenance-title">
              <span className="eyebrow">RETURNED PROVENANCE</span>
              <span>{response.provenance.length} record(s)</span>
            </div>
            {response.provenance.length === 0 ? (
              <p className="field-note">The API returned no provenance records.</p>
            ) : response.provenance.map((source, index) => (
              <div className="provenance-card" key={`${source.source_id}-${index}`}>
                <div className="provenance-heading">
                  <strong>{source.provider} · {source.source_type}</strong>
                  <span>{source.source_id}</span>
                </div>
                <p>{source.product}</p>
                <dl className="metadata-grid">
                  <div><dt>Source status</dt><dd>{response.data.source_verification_status}</dd></div>
                  <div><dt>Source names</dt><dd>{source.source_names.join(', ') || 'Not returned'}</dd></div>
                  <div><dt>Requested point</dt><dd>{source.latitude}, {source.longitude}</dd></div>
                  <div><dt>Reported point</dt><dd>{source.reported_latitude}, {source.reported_longitude}</dd></div>
                  <div><dt>Returned period</dt><dd>{source.returned_start_date} to {source.returned_end_date}</dd></div>
                  <div><dt>Retrieved</dt><dd>{source.retrieved_at}</dd></div>
                  <div><dt>Time standard</dt><dd>{source.time_standard}</dd></div>
                  <div><dt>Endpoint</dt><dd><a href={source.endpoint} target="_blank" rel="noreferrer">View provider endpoint</a></dd></div>
                </dl>
                <ul className="limitation-list">
                  {source.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}

export default EnvironmentalPanel
