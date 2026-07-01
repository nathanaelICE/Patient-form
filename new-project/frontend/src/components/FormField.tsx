import { ReactNode } from 'react'
interface Props {
  label: string
  name: string
  error?: string
  required?: boolean
  optional?: boolean
  className?: string
  children: ReactNode
}
export default function FormField({ label, name, error, required, optional, className, children }: Props) {
  return (
    <div className={`form-group${className ? ` ${className}` : ''}`}>
      <label htmlFor={name}>
        {label} {required && <span className="required">*</span>}
        {optional && <span className="optional">(optional)</span>}
      </label>
      {children}
      {error && <span className="form-error">{error}</span>}
    </div>
  )
}
