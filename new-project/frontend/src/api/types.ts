export type Gender = 'male' | 'female' | 'other'

export interface Patient {
  id: number
  name: string
  date_of_birth: string // ISO date
  gender: Gender
  phone: string | null
  employment_status: 'employed' | 'unemployed' | 'retired' | 'student' | null
  income: number | null
  created_at: string
}
export interface PatientCreate {
  name: string
  date_of_birth: string
  gender: Gender
  phone?: string | null
  employment_status?: 'employed' | 'unemployed' | 'retired' | 'student' | null
  income?: number | null
}
export type PatientUpdate = Partial<PatientCreate>

export interface Visit {
  id: number
  patient_id: number
  date: string
  chief_complaint: string
  diagnosis: string | null
  notes: string | null
  created_at: string
}
export interface VisitCreate {
  date: string
  chief_complaint: string
  diagnosis?: string | null
  notes?: string | null
}
export type VisitUpdate = Partial<VisitCreate>

export type ClaimStatus = 'approved' | 'denied' | 'pending'
export type ClaimType = 'inpatient' | 'outpatient' | 'emergency' | 'routine'
export type ClaimMethod = 'online' | 'paper' | 'phone'

export interface Claim {
  id: number
  patient_id: number
  visit_id: number | null
  claim_date: string
  claim_amount: number
  diagnosis_code: string | null
  procedure_code: string | null
  claim_status: ClaimStatus
  claim_type: ClaimType
  claim_submission_method: ClaimMethod
  provider_id: string | null
  provider_specialty: string | null
  provider_location: string | null
  created_at: string
}
export interface ClaimCreate {
  claim_date: string
  claim_amount: number
  visit_id?: number | null
  diagnosis_code?: string | null
  procedure_code?: string | null
  claim_status?: ClaimStatus
  claim_type: ClaimType
  claim_submission_method: ClaimMethod
  provider_id?: string | null
  provider_specialty?: string | null
  provider_location?: string | null
}
export type ClaimUpdate = Partial<ClaimCreate>

export interface Me {
  is_admin: boolean
}

export interface FieldError {
  loc: (string | number)[]
  msg: string
  type: string
}
