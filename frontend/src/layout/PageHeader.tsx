interface PageHeaderProps {
  index: string
  title: string
  description: string
}

export default function PageHeader({ index, title, description }: PageHeaderProps) {
  return (
    <header className="mb-8 border-b border-line pb-6">
      <p className="font-mono text-[11px] uppercase tracking-tag text-signal">
        {index}
      </p>
      <h2 className="mt-2 text-2xl font-semibold text-text">{title}</h2>
      <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">
        {description}
      </p>
    </header>
  )
}
