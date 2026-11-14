import { useEffect, useMemo, useState } from 'react'
import { explainApiError, getAgronomyEvidence } from '../api'
import type {
  AgronomyResponse,
  AgronomySource,
  CropCalendarClaim,
  CropTraitClaim,
} from '../types'

function SourceCitation({
  source,
  locator,
  geography,
  productionSystem,
  applicability,
}: {
  source: AgronomySource | undefined
  locator: string
  geography: string
  productionSystem: string
  applicability: string
}) {
  return (
    <div className="citation">
      <p>
        <strong>Source:</strong>{' '}
        {source
          ? <a href={source.url} target="_blank" rel="noreferrer">{source.title} ({source.provider})</a>
          : 'Source metadata was not returned'}
      </p>
      <dl className="metadata-grid">
        <div><dt>Locator</dt><dd>{locator}</dd></div>
        <div><dt>Geographic scope</dt><dd>{geography}</dd></div>
        <div><dt>Production system</dt><dd>{productionSystem}</dd></div>
        <div><dt>Time applicability</dt><dd>{applicability}</dd></div>
        {source && (
          <div><dt>Source status</dt><dd>{source.verification_status} · {source.time_applicability}</dd></div>
        )}
      </dl>
      {source && <p className="citation-note">{source.notes}</p>}
    </div>
  )
}

function TraitEvidence({
  claim,
  source,
}: {
  claim: CropTraitClaim
  source: AgronomySource | undefined
}) {
  return (
    <details className="evidence-item">
      <summary>
        <span><strong>{claim.crop_name}</strong><small>{claim.claim}</small></span>
        <span className="evidence-value">{claim.value}{claim.unit ? ` ${claim.unit}` : ''}</span>
      </summary>
      <div className="evidence-details">
        <p>{claim.notes}</p>
        <SourceCitation
          source={source}
          locator={claim.source_locator}
          geography={claim.geographic_scope}
          productionSystem={claim.production_system_scope}
          applicability={claim.time_applicability}
        />
        {claim.reference_period && <p className="field-note">Reference period: {claim.reference_period}</p>}
      </div>
    </details>
  )
}

function CalendarEvidence({
  claim,
  source,
}: {
  claim: CropCalendarClaim
  source: AgronomySource | undefined
}) {
  const start = claim.window_status === 'UNKNOWN' ? 'Unknown (not provided)' : claim.window_start ?? 'Not returned'
  const end = claim.window_status === 'UNKNOWN' ? 'Unknown (not provided)' : claim.window_end ?? 'Not returned'

  return (
    <details className="evidence-item">
      <summary>
        <span><strong>{claim.crop_name} · {claim.season}</strong><small>{claim.activity}</small></span>
        <span className="evidence-value">{claim.window_status === 'UNKNOWN' ? 'Dates unknown' : `${start} – ${end}`}</span>
      </summary>
      <div className="evidence-details">
        <p><strong>Window:</strong> {start} to {end}</p>
        {claim.timing_note && <p>{claim.timing_note}</p>}
        <p>{claim.notes}</p>
        <SourceCitation
          source={source}
          locator={claim.source_locator}
          geography={claim.geographic_scope}
          productionSystem={claim.production_system_scope}
          applicability={claim.time_applicability}
        />
      </div>
    </details>
  )
}

function AgronomyPanel() {
  const [response, setResponse] = useState<AgronomyResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    getAgronomyEvidence()
      .then((result) => {
        if (active) setResponse(result)
      })
      .catch((requestError: unknown) => {
        if (active) setError(explainApiError(requestError))
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => { active = false }
  }, [])

  const sourcesById = useMemo(
    () => new Map(response?.data.sources.map((source) => [source.source_id, source]) ?? []),
    [response],
  )

  return (
    <section className="panel agronomy-panel" aria-labelledby="agronomy-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">03 — CURATED SOURCES</p>
          <h2 id="agronomy-heading">Agronomy evidence</h2>
        </div>
        {response && (
          <span className="section-number">
            {response.data.crop_traits.length + response.data.crop_calendars.length} RECORDS
          </span>
        )}
      </div>
      {loading && <p className="notice notice-info" role="status">Loading cited evidence…</p>}
      {error && (
        <div className="notice notice-warning" role="alert">
          <strong>Evidence could not be loaded</strong>
          <p>{error}</p>
        </div>
      )}
      {!loading && !error && response && (
        <>
          <p className="scope-notice">{response.data.scope_notice}</p>
          <p className="section-intro">
            Published claims retain their original scope. They are evidence records, not
            current farm observations or crop recommendations.
          </p>
          <details className="source-list">
            <summary>{response.data.sources.length} source records</summary>
            <ul>
              {response.data.sources.map((source) => (
                <li key={source.source_id}>
                  <a href={source.url} target="_blank" rel="noreferrer">{source.title}</a>
                  <span>{source.provider} · {source.geographic_scope} · {source.time_applicability}</span>
                </li>
              ))}
            </ul>
          </details>

          <h3 className="subheading">Crop claims <span>{response.data.crop_traits.length}</span></h3>
          <div className="evidence-list">
            {response.data.crop_traits.map((claim) => (
              <TraitEvidence
                key={claim.record_id}
                claim={claim}
                source={sourcesById.get(claim.source_id)}
              />
            ))}
            {response.data.crop_traits.length === 0 && <p className="field-note">No crop claims were returned.</p>}
          </div>

          <h3 className="subheading">Calendar evidence <span>{response.data.crop_calendars.length}</span></h3>
          <div className="evidence-list">
            {response.data.crop_calendars.map((claim) => (
              <CalendarEvidence
                key={claim.record_id}
                claim={claim}
                source={sourcesById.get(claim.source_id)}
              />
            ))}
            {response.data.crop_calendars.length === 0 && <p className="field-note">No calendar records were returned.</p>}
          </div>
        </>
      )}
      {!loading && !error && !response && (
        <div className="empty-state"><p>No agronomy records were returned.</p></div>
      )}
    </section>
  )
}

export default AgronomyPanel
