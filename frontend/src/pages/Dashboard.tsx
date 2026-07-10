import PageHeader from '../layout/PageHeader'

const SUMMARY_CARDS = [
  { index: '01', label: 'Investigations', hint: 'Open and archived cases' },
  { index: '02', label: 'Connectors', hint: 'WHOIS · RDAP · crt.sh · Wayback · GitHub · Gravatar' },
  { index: '03', label: 'Unified Entities', hint: 'Deterministically correlated' },
  { index: '04', label: 'Reports', hint: 'Exportable PDF case files' },
]

export default function Dashboard() {
  return (
    <div>
      <PageHeader
        index="00 · Overview"
        title="Dashboard"
        description="Starting point for an investigator's session. Once wired up, this view will summarize active investigations, connector health, and recent correlation activity."
      />

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {SUMMARY_CARDS.map((card) => (
          <div
            key={card.index}
            className="rounded-sm border border-line bg-surface p-5"
          >
            <p className="font-mono text-[11px] text-faint">{card.index}</p>
            <p className="mt-3 text-sm font-medium text-text">{card.label}</p>
            <p className="mt-1 text-xs leading-relaxed text-muted">{card.hint}</p>
          </div>
        ))}
      </div>

      <div className="mt-8 rounded-sm border border-dashed border-line p-8 text-center">
        <p className="font-mono text-[11px] uppercase tracking-tag text-faint">
          Placeholder
        </p>
        <p className="mt-2 text-sm text-muted">
          No investigation data is wired up yet. This is a layout skeleton only.
        </p>
      </div>
    </div>
  )
}
