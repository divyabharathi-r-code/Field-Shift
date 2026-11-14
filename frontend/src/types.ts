export interface ApiWarning {
  code: string
  severity: string
  field_path: string | null
  message: string
}

export interface ApiConfidence {
  level: string
  coverage_pct: number | null
  reasons: string[]
}

export interface ApiSuccess<TData, TProvenance = Record<string, unknown>> {
  api_version: string
  data: TData
  provenance: TProvenance[]
  warnings: ApiWarning[]
  confidence: ApiConfidence
  run_id?: string | null
  engine_version?: string | null
  determinism_key?: string | null
}

export interface ApiProvenance {
  source_id: string
  [key: string]: unknown
}

export type EvidenceApplicability = 'HISTORICAL' | 'CURRENT' | 'UNKNOWN'
export type EvidenceStatus = 'VERIFIED' | 'UNVERIFIED'
export type ProductionSystem = 'IRRIGATED' | 'RAINFED' | 'UNKNOWN'
export type EvidenceKind = 'PUBLISHED_STATISTIC' | 'PUBLISHED_DESCRIPTIVE_CLAIM'

export interface AgronomySource {
  source_id: string
  provider: string
  title: string
  publication_year: number | null
  version: string | null
  url: string
  accessed_date: string
  geographic_scope: string
  source_kind: string
  verification_status: EvidenceStatus
  time_applicability: EvidenceApplicability
  notes: string
}

export interface CropTraitClaim {
  record_id: string
  crop_id: string
  crop_name: string
  claim: string
  value: string
  unit: string | null
  source_id: string
  source_locator: string
  geographic_scope: string
  production_system_scope: ProductionSystem
  evidence_kind: EvidenceKind
  evidence_status: EvidenceStatus
  time_applicability: EvidenceApplicability
  reference_period: string | null
  notes: string
}

export interface CropCalendarClaim {
  record_id: string
  crop_id: string
  crop_name: string
  season: string
  activity: string
  window_start: string | null
  window_end: string | null
  window_status: 'KNOWN' | 'UNKNOWN'
  timing_note: string | null
  source_id: string
  source_locator: string
  geographic_scope: string
  production_system_scope: ProductionSystem
  evidence_kind: EvidenceKind
  evidence_status: EvidenceStatus
  time_applicability: EvidenceApplicability
  reference_period: string | null
  notes: string
}

export interface AgronomyData {
  scope_notice: string
  sources: AgronomySource[]
  crop_traits: CropTraitClaim[]
  crop_calendars: CropCalendarClaim[]
}

export type AgronomyResponse = ApiSuccess<AgronomyData, ApiProvenance>

export interface EnvironmentalObservation {
  date: string
  parameter: string
  value: number | null
  units: string
  status: 'ok' | 'missing'
}

export interface NasaPowerProvenance {
  source_id: string
  source_type: 'PROVIDER_GRIDDED'
  provider: string
  product: string
  endpoint: string
  retrieved_at: string
  latitude: number
  longitude: number
  reported_latitude: number
  reported_longitude: number
  requested_start_date: string
  requested_end_date: string
  returned_start_date: string
  returned_end_date: string
  time_standard: string
  source_names: string[]
  parameters: string[]
  parameter_metadata: Array<{
    parameter: string
    units: string
    description: string
  }>
  limitations: string[]
}

export interface EnvironmentalData {
  experimental: true
  source_verification_status: 'unverified'
  observations: EnvironmentalObservation[]
}

export type EnvironmentalResponse = ApiSuccess<EnvironmentalData, NasaPowerProvenance>

export type RotationIssueCode =
  | 'INVALID_ENTRY'
  | 'INVALID_SEQUENCE_POSITION'
  | 'DUPLICATE_SEQUENCE_POSITION'
  | 'SEQUENCE_ORDER_MISMATCH'
  | 'MISSING_CROP_IDENTITY'
  | 'AMBIGUOUS_CROP_IDENTITY'
  | 'BLANK_CROP_IDENTITY'

export interface RotationValidationIssue {
  code: RotationIssueCode
  entry_index: number | null
  field: string
  message: string
}

export interface RotationValidationData {
  structurally_valid: boolean
  issues: RotationValidationIssue[]
  suitability_assessment: 'NOT_ASSESSED'
}

export type RotationValidationResponse = ApiSuccess<RotationValidationData>

export type RotationCropEntryRequest =
  | { sequence_position: number; crop_id: string; crop_name?: never }
  | { sequence_position: number; crop_name: string; crop_id?: never }

export interface RotationPlanRequest {
  entries: RotationCropEntryRequest[]
}
