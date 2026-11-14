import type {
  AgronomyResponse,
  EnvironmentalResponse,
  RotationPlanRequest,
  RotationValidationResponse,
} from './types'

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
).replace(/\/+$/, '')

export class ApiRequestError extends Error {
  readonly code: string | null
  readonly status: number

  constructor(message: string, status: number, code: string | null = null) {
    super(message)
    this.name = 'ApiRequestError'
    this.status = status
    this.code = code
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers)
  headers.set('Accept', 'application/json')
  if (init?.body) headers.set('Content-Type', 'application/json')

  const response = await fetch(url, { ...init, headers })
  let payload: unknown
  try {
    payload = await response.json()
  } catch {
    payload = null
  }

  if (!response.ok) {
    const error = isRecord(payload) && isRecord(payload.error)
      ? payload.error
      : undefined
    const code = typeof error?.code === 'string' ? error.code : null
    const message = typeof error?.message === 'string'
      ? error.message
      : `The API request failed with status ${response.status}.`
    throw new ApiRequestError(message, response.status, code)
  }

  if (!isRecord(payload)) {
    throw new ApiRequestError(
      'The API returned an empty or invalid JSON response.',
      response.status,
    )
  }
  return payload as T
}

export function getAgronomyEvidence(): Promise<AgronomyResponse> {
  return requestJson(`${API_BASE_URL}/api/v1/knowledge/agronomy`)
}

export function getDailyEnvironment(input: {
  latitude: number
  longitude: number
  start_date: string
  end_date: string
}): Promise<EnvironmentalResponse> {
  const query = new URLSearchParams({
    latitude: String(input.latitude),
    longitude: String(input.longitude),
    start_date: input.start_date,
    end_date: input.end_date,
  })
  return requestJson(
    `${API_BASE_URL}/api/v1/environmental/daily?${query.toString()}`,
  )
}

export function validateRotationPlan(
  plan: RotationPlanRequest,
): Promise<RotationValidationResponse> {
  return requestJson(`${API_BASE_URL}/api/v1/rotations/validate`, {
    method: 'POST',
    body: JSON.stringify(plan),
  })
}

export function explainApiError(error: unknown): string {
  if (error instanceof ApiRequestError) {
    if (error.code === 'SOURCE_DISABLED') {
      return 'NASA POWER access is disabled by the backend. No substitute data are shown.'
    }
    if (error.code === 'PROVIDER_UNAVAILABLE') {
      return 'NASA POWER data are unavailable for this request. The backend may be offline without a matching cache entry.'
    }
    return `${error.code ? `${error.code}: ` : ''}${error.message}`
  }
  if (error instanceof TypeError) {
    return 'Could not reach the API. Check that the backend is running and the frontend origin is allowed by CORS.'
  }
  return error instanceof Error ? error.message : 'An unexpected request error occurred.'
}
