export type Gender = 'male' | 'female' | 'other'

export interface Patient {
  id: number
  name: string
  date_of_birth: string // ISO date
  gender: Gender
  phone: string | null
  created_at: string
}
export interface PatientCreate {
  name: string
  date_of_birth: string
  gender: Gender
  phone?: string | null
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

export interface Me {
  is_admin: boolean
}

export interface FieldError {
  loc: (string | number)[]
  msg: string
  type: string
}
