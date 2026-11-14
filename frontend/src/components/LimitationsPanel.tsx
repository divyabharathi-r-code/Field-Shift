function LimitationsPanel() {
  return (
    <aside className="limitations-panel" aria-labelledby="limitations-heading">
      <div className="limitations-heading">
        <p className="eyebrow">READ BEFORE INTERPRETING</p>
        <h2 id="limitations-heading">What this workbench does not know</h2>
      </div>
      <ul>
        <li><strong>NASA POWER is gridded context.</strong> It is not a farm-station measurement or a field-scale observation.</li>
        <li><strong>District evidence is not farm-specific.</strong> Published Madurai claims retain their own source, place, system, and time scope.</li>
        <li><strong>Structure is not suitability.</strong> A valid sequence does not establish agronomic compatibility or resilience.</li>
        <li><strong>Missing evidence stays missing.</strong> Unknown dates and unavailable environmental data are never filled with invented values.</li>
      </ul>
    </aside>
  )
}

export default LimitationsPanel
