interface EmptyStateProps {
  icon?: React.ReactNode
  title: string
  description: string
  action?: {
    label: string
    onClick: () => void
  }
}

export default function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex min-h-[400px] items-center justify-center rounded-sm border border-dashed border-line bg-scan p-12">
      <div className="max-w-md text-center">
        {icon && <div className="mb-4 flex justify-center text-faint">{icon}</div>}
        <h3 className="text-base font-semibold text-text">{title}</h3>
        <p className="mt-2 text-sm leading-relaxed text-muted">{description}</p>
        {action && (
          <button
            onClick={action.onClick}
            className="mt-6 rounded border border-signal bg-signalDim px-4 py-2 text-sm font-medium text-signal transition-colors hover:bg-signal/20 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-signal"
          >
            {action.label}
          </button>
        )}
      </div>
    </div>
  )
}
