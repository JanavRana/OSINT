import PageHeader from '../layout/PageHeader'

export default function Graph() {
  return (
    <div>
      <PageHeader
        index="02 · Relationships"
        title="Graph"
        description="Interactive Cytoscape.js relationship graph will render here — unified entities as nodes, evidence-backed relationships as edges."
      />

      <div className="flex h-[420px] items-center justify-center rounded-sm border border-dashed border-line">
        <div className="text-center">
          <p className="font-mono text-[11px] uppercase tracking-tag text-faint">
            Placeholder
          </p>
          <p className="mt-2 text-sm text-muted">Graph canvas not yet implemented.</p>
        </div>
      </div>
    </div>
  )
}
