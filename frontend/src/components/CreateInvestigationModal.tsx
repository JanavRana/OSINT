import { useState } from 'react'

interface CreateInvestigationModalProps {
  isOpen: boolean
  onClose: () => void
  onCreate: (name: string, description: string) => void
}

export default function CreateInvestigationModal({
  isOpen,
  onClose,
  onCreate,
}: CreateInvestigationModalProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')

  if (!isOpen) return null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (name.trim()) {
      onCreate(name.trim(), description.trim())
      setName('')
      setDescription('')
      onClose()
    }
  }

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose()
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/80 backdrop-blur-sm"
      onClick={handleBackdropClick}
    >
      <div className="w-full max-w-lg rounded border border-line bg-surface p-6 shadow-xl">
        <div className="mb-4 border-b border-line pb-4">
          <h3 className="text-lg font-semibold text-text">Create Investigation</h3>
          <p className="mt-1 text-sm text-muted">
            Start a new case with identifiers to investigate
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="space-y-4">
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-text">
                Investigation Name <span className="text-danger">*</span>
              </label>
              <input
                type="text"
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Case 2026-0417"
                className="mt-1.5 w-full rounded border border-line bg-surface2 px-3 py-2 text-sm text-text placeholder-faint focus:border-signal focus:outline-none focus:ring-1 focus:ring-signal"
                required
                autoFocus
              />
            </div>

            <div>
              <label htmlFor="description" className="block text-sm font-medium text-text">
                Description <span className="text-xs text-muted">(optional)</span>
              </label>
              <textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Brief description of the investigation..."
                rows={3}
                className="mt-1.5 w-full rounded border border-line bg-surface2 px-3 py-2 text-sm text-text placeholder-faint focus:border-signal focus:outline-none focus:ring-1 focus:ring-signal"
              />
            </div>
          </div>

          <div className="mt-6 flex justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="rounded border border-line px-4 py-2 text-sm font-medium text-muted transition-colors hover:bg-surface2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-line"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!name.trim()}
              className="rounded border border-signal bg-signalDim px-4 py-2 text-sm font-medium text-signal transition-colors hover:bg-signal/20 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-signal disabled:cursor-not-allowed disabled:opacity-50"
            >
              Create Investigation
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
