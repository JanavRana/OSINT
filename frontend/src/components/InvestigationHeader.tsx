import type { Investigation } from '../types/investigation'
import StatusBadge from './StatusBadge'

interface InvestigationHeaderProps {
  investigation: Investigation
}

export default function InvestigationHeader({ investigation }: InvestigationHeaderProps) {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date)
  }

  return (
    <div className="mb-8 rounded border border-line bg-surface p-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold text-text">{investigation.name}</h1>
            <StatusBadge status={investigation.status} />
          </div>
          {investigation.description && (
            <p className="mt-2 text-sm leading-relaxed text-muted">
              {investigation.description}
            </p>
          )}
        </div>

        <div className="flex flex-col gap-2 md:items-end">
          <div className="text-xs text-faint">
            <span className="font-mono uppercase tracking-tag">Created</span>
          </div>
          <div className="font-mono text-sm text-muted">
            {formatDate(investigation.createdAt)}
          </div>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-2 gap-4 border-t border-line pt-4 md:grid-cols-4">
        <div>
          <div className="text-xs font-mono uppercase tracking-tag text-faint">
            Investigation ID
          </div>
          <div className="mt-1 font-mono text-sm text-muted">{investigation.id}</div>
        </div>
        <div>
          <div className="text-xs font-mono uppercase tracking-tag text-faint">
            Identifiers
          </div>
          <div className="mt-1 text-sm font-semibold text-text">
            {investigation.identifierCount}
          </div>
        </div>
        <div>
          <div className="text-xs font-mono uppercase tracking-tag text-faint">
            Entities Found
          </div>
          <div className="mt-1 text-sm font-semibold text-text">
            {investigation.entityCount}
          </div>
        </div>
        <div>
          <div className="text-xs font-mono uppercase tracking-tag text-faint">
            Status
          </div>
          <div className="mt-1 text-sm text-muted capitalize">
            {investigation.status}
          </div>
        </div>
      </div>
    </div>
  )
}
