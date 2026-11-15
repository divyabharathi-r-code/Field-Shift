# FieldShift 🌱

**NASA Space Apps Challenge 2026 — Field Shift: Adapting Farms with NASA Data**

### An evidence-first farm rotation workbench

**Make the evidence visible. Keep the unknowns honest.**

FieldShift is a web-based workbench that brings together curated agronomy evidence, optional NASA POWER environmental context, and structural validation of user-supplied crop sequences.

It is designed to help users explore what available evidence says, where that evidence applies, and what remains unknown.

FieldShift does **not** recommend crops or claim that a crop rotation is suitable for a particular farm.

---

## The problem

Exploring crop rotations requires understanding more than a list of crops. Environmental context, locally documented agronomy information, geographic applicability, and missing evidence all matter.

However, these sources are not always presented together, and incomplete information can easily be mistaken for certainty.

## Our approach

FieldShift brings three capabilities into one workbench:

1. **Agronomy evidence explorer** — displays curated crop traits and calendar records alongside their sources, source locations, geographic scope, production-system context, and applicability.
2. **Environmental context** — integrates a NASA POWER daily-data provider for point coordinates and date ranges. The integration is disabled by default while provider verification remains unresolved.
3. **Rotation structure validator** — lets users create and edit a crop sequence and checks its structural validity, including sequence positions and crop identity fields.

The result makes evidence and limitations visible rather than hiding uncertainty behind a score.

---

## Features

### 1. Agronomy evidence explorer
- Browse curated crop-trait and crop-calendar claims.
- View source references and source locators.
- Inspect geographic and production-system scope.
- See unknown calendar windows explicitly instead of receiving guessed dates.
- Distinguish claim verification from farm-specific applicability.

### 2. NASA POWER environmental integration
- Accepts a point location and date range.
- Integrates NASA POWER daily environmental parameters.
- Preserves provider provenance and missing-data information.
- Identifies gridded environmental data as gridded context, not farm-station observations.
- Handles disabled and unavailable provider states without inventing fallback observations.

**Important:** NASA POWER integration is disabled by default in the current MVP. The provider's verification remains unresolved. The default demo therefore does not claim to display live NASA observations.

### 3. Crop rotation structure validation
- Add, remove, and reorder crop entries.
- Accept crop identifiers or crop names.
- Validate sequence structure and positions.
- Preserve user-submitted order and repeated crops.
- Return machine-readable validation issues.

**Important:** Structural validity is not agronomic suitability. The application explicitly reports `NOT_ASSESSED` for suitability.

---

## Technology stack

| Layer | Technologies |
|---|---|
| Frontend | React, TypeScript, Vite |
| Backend | Python 3.12+, FastAPI, Pydantic |
| Testing | pytest |
| Code quality | Ruff, Import Linter |
| Environmental data | NASA POWER daily API integration |
| Evidence registry | Curated agronomy source and claim records |

---

## Architecture

```text
User
  |
  v
React + TypeScript Workbench
  |
  v
FastAPI
  |
  +---- Agronomy Knowledge API
  |       |
  |       +---- Curated evidence registry
  |
  +---- Environmental API
  |       |
  |       +---- NASA POWER provider
  |
  +---- Rotation Validation API
          |
          +---- Pure structural validation engine
```

The rotation validation engine is kept independent of HTTP and external network clients. The application uses explicit contracts and provenance to keep data interpretation transparent.

---

## Running FieldShift locally

### Prerequisites

- Python 3.12 or later
- Node.js and npm
- Git

### 1. Clone the repository

```bash
git clone https://github.com/divyabharathi-r-code/field-shift.git
cd field-shift
```

Make sure you are using the `phase-2/nasa-data-layer` branch:

```bash
git checkout phase-2/nasa-data-layer
```

### 2. Start the backend

Open a terminal:

```bash
cd backend

python -m venv .venv
```

Activate the virtual environment.

**Windows PowerShell:**

```powershell
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
source .venv/bin/activate
```

Install the backend and development dependencies:

```bash
pip install -e ".[dev]"
```

Start the API:

```bash
uvicorn app.main:app --reload
```

Backend:
`http://localhost:8000`

API documentation:
`http://localhost:8000/docs`

### 3. Start the frontend

Open a second terminal:

```bash
cd frontend
npm install
```

The default API URL is already configured as:

```text
http://localhost:8000
```

To use the provided example environment file, copy `.env.example` to `.env`.

**Windows PowerShell:**

```powershell
Copy-Item .env.example .env
```

**macOS / Linux:**

```bash
cp .env.example .env
```

Start the frontend:

```bash
npm run dev
```

Open the local Vite URL shown in your terminal, usually:

`http://localhost:5173`

Keep both backend and frontend terminals running while using the application.

---

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/v1/health` | Backend health check |
| GET | `/api/v1/knowledge/agronomy` | Retrieve curated agronomy evidence |
| GET | `/api/v1/environmental/daily` | Request daily environmental context |
| POST | `/api/v1/rotations/validate` | Validate a user-supplied crop sequence |

Interactive API documentation is available at `/docs` when the backend is running.

---

## Data sources and provenance

### NASA POWER

NASA POWER provides gridded environmental data through its daily API.

Documentation: https://power.larc.nasa.gov/docs/services/api/temporal/daily/

FieldShift integrates daily precipitation and temperature parameters. The integration is disabled by default pending provider verification.

NASA POWER grid values must not be interpreted as direct measurements from an individual farm.

### Agronomy evidence

The curated evidence registry includes references to:

- Tamil Nadu Agricultural University (TNAU), Madurai District Agriculture Plan, 2017–18.
- Madurai District Agriculture portal.
- TNAU Krishi Vigyan Kendra (KVK), Madurai — Major Crops.

The records retain source references, locators, scope, and applicability information.

Historical district-level evidence should not automatically be interpreted as current farm-level guidance.

---

## Scientific integrity and limitations

FieldShift deliberately avoids claims that its available evidence cannot support.

- It does not recommend crops or rank crop rotations.
- It does not calculate agronomic suitability.
- It does not infer missing crop-calendar dates or rotation rules.
- It does not infer farm-specific soil or irrigation conditions.
- It does not generate fabricated environmental observations.
- It does not treat gridded environmental data as farm-station measurements.
- It distinguishes verified source claims from current local or farm-specific applicability.

A structurally valid crop sequence is not necessarily agronomically suitable.

Missing evidence means that the relevant question remains unassessed, not that a crop is unsuitable.

---

## Testing and quality checks

From the `backend/` directory, with the virtual environment activated:

```bash
pytest -q -ra
ruff check .
lint-imports
```

The frontend production build can be checked from `frontend/`:

```bash
npm run build
```

---

## Challenge alignment

FieldShift addresses the NASA Space Apps Challenge 2026 challenge:

**Field Shift — Adapting Farms with NASA Data**

The project explores how environmental context and documented agronomy evidence can be presented together while keeping uncertainty, provenance, and applicability visible.

Our goal is not to replace local agricultural expertise. It is to make the available evidence easier to inspect and its limitations easier to understand.

---

## Project status

**Phase 2F — Evidence-first demo workbench completed.**

The current MVP includes:
- Curated agronomy evidence registry and API.
- NASA POWER environmental provider integration.
- Rotation-plan contract and structural validation engine.
- Rotation validation API.
- React + TypeScript frontend workbench.
- Backend tests and frontend production build.

The project is maintained as an evidence-first exploration tool, with further agronomic modelling intentionally outside the current MVP scope.

---

**Built for NASA Space Apps Challenge 2026.**

🌱 **FieldShift — Make the evidence visible. Keep the unknowns honest.**