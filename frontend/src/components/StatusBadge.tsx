import type { InvestigationStatus } from '../types/investigation'

interface StatusBadgeProps {
  status: InvestigationStatus
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const styles = {
    pending: 'bg-surface2 text-muted border-line',
    running: 'bg-signalDim text-signal border-signal/30',
    completed: 'bg-signalDim text-signal border-signal',
    failed: 'bg-danger/10 text-danger border-danger/30',
  }

  const labels = {
    pending: 'Pending',
    running: 'Running',
    completed: 'Completed',
    failed: 'Failed',
  }

  return (
    <span
      className={`inline-flex items-center rounded border px-2 py-0.5 font-mono text-[10px] uppercase tracking-tag ${styles[status]}`}
    >
      {status === 'running' && (
        <span className="mr-1.5 h-1.5 w-1.5 animate-pulse rounded-full bg-signal"></span>
      )}
      {labels[status]}
    </span>
  )
}
