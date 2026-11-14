import { useState } from 'react'
import AgronomyPanel from './components/AgronomyPanel'
import EnvironmentalPanel from './components/EnvironmentalPanel'
import LimitationsPanel from './components/LimitationsPanel'
import LocationForm, { type FarmLocation } from './components/LocationForm'
import RotationBuilder from './components/RotationBuilder'

function App() {
  const [location, setLocation] = useState<FarmLocation | null>(null)

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="wordmark" href="#top" aria-label="FieldShift home">
          <span className="wordmark-mark" aria-hidden="true">F</span>
          <span>FIELD<span className="wordmark-light">SHIFT</span></span>
        </a>
        <div className="topbar-status">
          <span className="status-dot" />
          Evidence-first workbench
        </div>
      </header>

      <main id="top">
        <section className="hero">
          <p className="eyebrow">NASA SPACE APPS CHALLENGE 2026</p>
          <h1>Make the evidence visible.<br /><em>Keep the unknowns honest.</em></h1>
          <p className="hero-copy">
            Explore published agronomy evidence and optional NASA POWER context for a
            user-selected point. Validate a rotation sequence you provide; FieldShift
            does not recommend what to plant.
          </p>
          <div className="hero-meta">
            <span>01 / Location</span>
            <span>02 / NASA context</span>
            <span>03 / Agronomy evidence</span>
            <span>04 / User-supplied plan</span>
          </div>
        </section>

        <section className="panel location-panel" aria-labelledby="location-heading">
          <div className="section-heading">
            <div>
              <p className="eyebrow">01 — YOUR INPUT</p>
              <h2 id="location-heading">Set a point location</h2>
            </div>
            <span className="section-number">PROFILE</span>
          </div>
          <p className="section-intro">
            Coordinates are user-supplied point context, not a farm boundary. No area,
            soil, or irrigation conditions are inferred.
          </p>
          <LocationForm onSubmit={setLocation} />
          {location && (
            <div className="active-location" role="status">
              <span className="active-location-label">ACTIVE DEMO POINT</span>
              <strong>{location.label}</strong>
              <span>{location.latitude.toFixed(4)}, {location.longitude.toFixed(4)}</span>
            </div>
          )}
        </section>

        <EnvironmentalPanel location={location} />

        <div className="content-grid">
          <AgronomyPanel />
          <RotationBuilder />
        </div>

        <LimitationsPanel />
      </main>

      <footer className="footer">
        <span>FIELDSHIFT · EVIDENCE-FIRST DEMONSTRATION</span>
        <span>Unknown remains unknown.</span>
      </footer>
    </div>
  )
}

export default App
