import PageHeader from '../layout/PageHeader'

export default function Investigations() {
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
      </div>
    </div>
  )
}
