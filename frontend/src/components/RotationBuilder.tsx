import { useState, type FormEvent } from 'react'
import { explainApiError, validateRotationPlan } from '../api'
import type {
  RotationPlanRequest,
  RotationValidationData,
} from '../types'

type IdentityKind = 'crop_id' | 'crop_name'

interface DraftEntry {
  id: number
  identityKind: IdentityKind
  value: string
}

function RotationBuilder() {
  const [entries, setEntries] = useState<DraftEntry[]>([
    { id: 1, identityKind: 'crop_name', value: '' },
  ])
  const [nextId, setNextId] = useState(2)
  const [result, setResult] = useState<RotationValidationData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [inputError, setInputError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  function updateEntries(updater: (current: DraftEntry[]) => DraftEntry[]) {
    setEntries(updater)
    setResult(null)
    setError(null)
    setInputError(null)
  }

  function moveEntry(index: number, direction: -1 | 1) {
    updateEntries((current) => {
      const destination = index + direction
      if (destination < 0 || destination >= current.length) return current
      const reordered = [...current]
      ;[reordered[index], reordered[destination]] = [reordered[destination], reordered[index]]
      return reordered
    })
  }

  function addEntry() {
    updateEntries((current) => [...current, {
      id: nextId,
      identityKind: 'crop_name',
      value: '',
    }])
    setNextId((current) => current + 1)
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setInputError(null)
    setResult(null)

    if (entries.length === 0) {
      setInputError('Add at least one crop entry before validating.')
      return
    }
    const blankEntry = entries.findIndex((entry) => !entry.value.trim())
    if (blankEntry !== -1) {
      setInputError(`Enter a crop ${entries[blankEntry].identityKind === 'crop_id' ? 'ID' : 'name'} for entry ${blankEntry + 1}.`)
      return
    }

    const plan: RotationPlanRequest = {
      entries: entries.map((entry, index) => entry.identityKind === 'crop_id'
        ? { sequence_position: index + 1, crop_id: entry.value.trim() }
        : { sequence_position: index + 1, crop_name: entry.value.trim() }),
    }

    setLoading(true)
    try {
      const response = await validateRotationPlan(plan)
      setResult(response.data)
    } catch (requestError) {
      setError(explainApiError(requestError))
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="panel rotation-panel" aria-labelledby="rotation-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">04 — YOUR SEQUENCE</p>
          <h2 id="rotation-heading">Rotation structure</h2>
        </div>
        <span className="section-number">{entries.length} ENTRIES</span>
      </div>
      <p className="section-intro">
        Enter and order crop identities yourself. Sequence positions are assigned
        contiguously from the displayed order; repeated crops are allowed.
      </p>

      <form onSubmit={handleSubmit}>
        <div className="rotation-entries">
          {entries.map((entry, index) => (
            <fieldset className="rotation-entry" key={entry.id} disabled={loading}>
              <legend>Sequence {index + 1}</legend>
              <div className="rotation-entry-row">
                <span className="sequence-number">{String(index + 1).padStart(2, '0')}</span>
                <label className="field identity-kind">
                  <span>Identity type</span>
                  <select
                    value={entry.identityKind}
                    onChange={(event) => {
                      const identityKind: IdentityKind = event.target.value === 'crop_id'
                        ? 'crop_id'
                        : 'crop_name'
                      updateEntries((current) => current.map((item) => item.id === entry.id
                        ? { ...item, identityKind }
                        : item))
                    }}
                  >
                    <option value="crop_name">Crop name</option>
                    <option value="crop_id">Crop ID</option>
                  </select>
                </label>
                <label className="field crop-identity">
                  <span>{entry.identityKind === 'crop_id' ? 'Caller-supplied crop ID' : 'User-entered crop name'}</span>
                  <input
                    value={entry.value}
                    onChange={(event) => updateEntries((current) => current.map((item) => item.id === entry.id
                      ? { ...item, value: event.target.value }
                      : item))}
                    placeholder={entry.identityKind === 'crop_id' ? 'Enter an ID' : 'Enter a crop name'}
                    required
                  />
                </label>
                <div className="entry-actions" aria-label={`Reorder or remove sequence ${index + 1}`}>
                  <button
                    className="icon-button"
                    type="button"
                    onClick={() => moveEntry(index, -1)}
                    disabled={loading || index === 0}
                    aria-label={`Move sequence ${index + 1} up`}
                    title="Move up"
                  >↑</button>
                  <button
                    className="icon-button"
                    type="button"
                    onClick={() => moveEntry(index, 1)}
                    disabled={loading || index === entries.length - 1}
                    aria-label={`Move sequence ${index + 1} down`}
                    title="Move down"
                  >↓</button>
                  <button
                    className="icon-button icon-button-remove"
                    type="button"
                    onClick={() => updateEntries((current) => current.filter((item) => item.id !== entry.id))}
                    disabled={loading}
                    aria-label={`Remove sequence ${index + 1}`}
                    title="Remove entry"
                  >×</button>
                </div>
              </div>
            </fieldset>
          ))}
        </div>

        <div className="rotation-actions">
          <button className="button button-outline" type="button" onClick={addEntry} disabled={loading}>
            + Add crop
          </button>
          <button className="button button-dark" type="submit" disabled={loading}>
            {loading ? 'Validating…' : 'Validate structure'}
          </button>
        </div>
      </form>

      <p className="field-note">
        No crop catalogue is assumed. The API checks structure only; it does not
        generate or recommend crop sequences.
      </p>

      {inputError && <p className="form-error" role="alert">{inputError}</p>}
      {error && (
        <div className="notice notice-warning" role="alert">
          <strong>Validation request failed</strong>
          <p>{error}</p>
        </div>
      )}
      {result && (
        <div className={`validation-result ${result.structurally_valid ? 'result-valid' : 'result-invalid'}`} aria-live="polite">
          <div className="result-heading">
            <div>
              <span className="eyebrow">ENGINE RESULT</span>
              <h3>{result.structurally_valid ? 'Structure is valid' : 'Structural issues found'}</h3>
            </div>
            <span className={`result-state ${result.structurally_valid ? 'state-valid' : 'state-invalid'}`}>
              {result.structurally_valid ? 'VALID' : 'ISSUES'}
            </span>
          </div>
          <div className="assessment-banner">
            <span>AGRONOMIC SUITABILITY</span>
            <strong>{result.suitability_assessment}</strong>
          </div>
          {result.issues.length > 0 ? (
            <ul className="issue-list">
              {result.issues.map((issue, index) => (
                <li key={`${issue.code}-${issue.entry_index}-${issue.field}-${index}`}>
                  <span className="issue-code">{issue.code}</span>
                  <span className="issue-location">
                    {issue.entry_index === null ? 'Plan' : `Entry ${issue.entry_index + 1}`}
                    {' · '}{issue.field}
                  </span>
                  <p>{issue.message}</p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="field-note">The supplied sequence has a structurally valid representation only.</p>
          )}
        </div>
      )}
    </section>
  )
}

export default RotationBuilder
