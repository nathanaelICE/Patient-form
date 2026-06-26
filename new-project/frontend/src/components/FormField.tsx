import { ReactNode } from 'react'
interface Props { label: string; name: string; error?: string; children: ReactNode }
export default function FormField({ label, name, error, children }: Props) {
  return (
    <div className="form-field">
      <label htmlFor={name}>{label}</label>
      {children}
      {error && <span className="field-error">{error}</span>}
    </div>
  )
}
