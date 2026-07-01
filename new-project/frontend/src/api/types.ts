export type Gender = 'male' | 'female' | 'other'

export interface Patient {
  id: number
  name: string
  date_of_birth: string // ISO date
  gender: Gender
  phone: string | null
  national_id: string | null
  place_of_birth: string | null
  marital_status: string | null
  occupation: string | null
  religion: string | null
  nationality: string | null
  blood_type: string | null
  allergies: string | null
  known_conditions: string | null
  created_at: string
}
export interface PatientCreate {
  name: string
  date_of_birth: string
  gender: Gender
  phone?: string | null
  national_id?: string | null
  place_of_birth?: string | null
  marital_status?: string | null
  occupation?: string | null
  religion?: string | null
  nationality?: string | null
  blood_type?: string | null
  allergies?: string | null
  known_conditions?: string | null
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
