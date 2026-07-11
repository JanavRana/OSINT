import { useNavigate } from 'react-router-dom'
import PageHeader from '../layout/PageHeader'

export default function Investigations() {
  const navigate = useNavigate()

  const handleViewDetails = () => {
    // Navigate to mock investigation details
    navigate('/investigations/inv-2026-001')
  }

  return (
    <div>
      <PageHeader
        index="01 · Cases"
        title="Investigations"
        description="List and detail view for investigations will live here — creating a new case, adding identifiers, and reviewing per-connector execution status."
      />

      <div className="rounded-sm border border-dashed border-line p-16 text-center">
        <p className="font-mono text-[11px] uppercase tracking-tag text-faint">
          Placeholder
        </p>
        <p className="mt-2 text-sm text-muted">
          Investigation list, creation form, and status polling are not yet implemented.
        </p>
        <button
          onClick={handleViewDetails}
          className="mt-4 rounded border border-signal bg-signalDim px-4 py-2 text-sm font-medium text-signal transition-colors hover:bg-signal/20"
        >
          View Sample Investigation Details
        </button>
      </div>
    </div>
  )
}
