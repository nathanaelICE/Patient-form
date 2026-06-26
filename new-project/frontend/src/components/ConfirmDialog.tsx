interface Props {
  open: boolean
  title: string
  message: string
  confirmLabel?: string
  onConfirm: () => void
  onCancel: () => void
}
export default function ConfirmDialog({ open, title, message, confirmLabel = 'Delete', onConfirm, onCancel }: Props) {
  if (!open) return null
  return (
    <div className="modal-overlay" role="dialog" aria-modal="true">
      <div className="modal-dialog">
        <h2 className="modal-title">{title}</h2>
        <p>{message}</p>
        <div className="modal-actions">
          <button className="btn btn-secondary" onClick={onCancel}>Cancel</button>
          <button className="btn btn-danger" onClick={onConfirm}>{confirmLabel}</button>
        </div>
      </div>
    </div>
  )
}
