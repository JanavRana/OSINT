export type ExecutionStatusType = 'not_started' | 'running' | 'completed' | 'failed'

interface ExecutionStatusProps {
  status: ExecutionStatusType
  message?: string
}

export default function ExecutionStatus({ status, message }: ExecutionStatusProps) {
  const configs = {
    not_started: {
      icon: (
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
          />
        </svg>
      ),
      bgColor: 'bg-surface2',
      textColor: 'text-muted',
      borderColor: 'border-line',
      label: 'Not Started',
      defaultMessage: 'Add identifiers and click "Execute Investigation" to begin.',
    },
    running: {
      icon: (
        <svg className="h-5 w-5 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      ),
      bgColor: 'bg-signalDim',
      textColor: 'text-signal',
      borderColor: 'border-signal/30',
      label: 'Running',
      defaultMessage: 'Investigation is currently running...',
    },
    completed: {
      icon: (
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      ),
      bgColor: 'bg-signalDim',
      textColor: 'text-signal',
      borderColor: 'border-signal',
      label: 'Completed',
      defaultMessage: 'Investigation completed successfully.',
    },
    failed: {
      icon: (
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      ),
      bgColor: 'bg-danger/10',
      textColor: 'text-danger',
      borderColor: 'border-danger/30',
      label: 'Failed',
      defaultMessage: 'Investigation failed to complete.',
    },
  }

  const config = configs[status]

  return (
    <div
      className={`rounded border ${config.borderColor} ${config.bgColor} p-4`}
    >
      <div className="flex items-start gap-3">
        <div className={`flex-shrink-0 ${config.textColor}`}>{config.icon}</div>
        <div className="flex-1">
          <div className={`font-medium ${config.textColor}`}>{config.label}</div>
          <p className="mt-1 text-sm text-muted">
            {message || config.defaultMessage}
          </p>
        </div>
      </div>
    </div>
  )
}
