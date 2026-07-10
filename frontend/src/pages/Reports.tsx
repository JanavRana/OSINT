import PageHeader from '../layout/PageHeader'

export default function Reports() {
  return (
    <div>
      <PageHeader
        index="04 · Export"
        title="Reports"
        description="On-demand PDF report generation and download will live here — executive summary, unified profiles, graph snapshot, timeline, and evidence appendix."
      />

      <div className="rounded-sm border border-dashed border-line p-16 text-center">
        <p className="font-mono text-[11px] uppercase tracking-tag text-faint">
          Placeholder
        </p>
        <p className="mt-2 text-sm text-muted">Report generation not yet implemented.</p>
      </div>
    </div>
  )
}
