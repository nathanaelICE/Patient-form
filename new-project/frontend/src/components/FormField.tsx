import { ReactNode } from 'react'
interface Props {
  label: string
  name: string
  error?: string
  required?: boolean
  optional?: boolean
  children: ReactNode
}
export default function FormField({ label, name, error, required, optional, children }: Props) {
  return (
    <div className="form-group">
      <label htmlFor={name}>
        {label} {required && <span className="required">*</span>}
        {optional && <span className="optional">(optional)</span>}
      </label>
      {children}
      {error && <span className="form-error">{error}</span>}
    </div>
  )
}
