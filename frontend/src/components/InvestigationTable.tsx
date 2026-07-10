import type { Investigation } from '../types/investigation'
import StatusBadge from './StatusBadge'

interface InvestigationTableProps {
  investigations: Investigation[]
  onSelect: (investigation: Investigation) => void
}

export default function InvestigationTable({ investigations, onSelect }: InvestigationTableProps) {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date)
  }

  return (
    <div className="overflow-hidden rounded border border-line bg-surface">
      <table className="w-full border-collapse">
        <thead>
          <tr className="border-b border-line bg-surface2">
            <th className="px-4 py-3 text-left font-mono text-[10px] uppercase tracking-tag text-faint">
              Name
            </th>
            <th className="px-4 py-3 text-left font-mono text-[10px] uppercase tracking-tag text-faint">
              Status
            </th>
            <th className="px-4 py-3 text-left font-mono text-[10px] uppercase tracking-tag text-faint">
              Identifiers
            </th>
            <th className="px-4 py-3 text-left font-mono text-[10px] uppercase tracking-tag text-faint">
              Entities
            </th>
            <th className="px-4 py-3 text-left font-mono text-[10px] uppercase tracking-tag text-faint">
              Created
            </th>
          </tr>
        </thead>
        <tbody>
          {investigations.map((investigation) => (
            <tr
              key={investigation.id}
              onClick={() => onSelect(investigation)}
              className="cursor-pointer border-b border-line transition-colors last:border-b-0 hover:bg-surface2"
            >
              <td className="px-4 py-3">
                <div className="font-medium text-text">{investigation.name}</div>
                {investigation.description && (
                  <div className="mt-1 text-sm text-muted">{investigation.description}</div>
                )}
              </td>
              <td className="px-4 py-3">
                <StatusBadge status={investigation.status} />
              </td>
              <td className="px-4 py-3 text-sm text-muted">
                {investigation.identifierCount}
              </td>
              <td className="px-4 py-3 text-sm text-muted">
                {investigation.entityCount}
              </td>
              <td className="px-4 py-3 font-mono text-xs text-muted">
                {formatDate(investigation.createdAt)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
