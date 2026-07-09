import PageHeader from '../layout/PageHeader'

export default function Timeline() {
  return (
    <div>
      <PageHeader
        index="03 · Chronology"
        title="Timeline"
        description="Chronological list of dated events (domain registration, certificate issuance, archive snapshots) will render here, with filters by entity and event type."
      />

      <div className="rounded-sm border border-dashed border-line p-16 text-center">
        <p className="font-mono text-[11px] uppercase tracking-tag text-faint">
          Placeholder
        </p>
        <p className="mt-2 text-sm text-muted">Timeline view not yet implemented.</p>
      </div>
    </div>
  )
}
