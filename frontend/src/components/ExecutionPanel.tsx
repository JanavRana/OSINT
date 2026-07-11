import { useState } from 'react'
import type { IdentifierType, Identifier } from '../types/investigation'
import IdentifierInput from './IdentifierInput'
import ExecutionStatus, { type ExecutionStatusType } from './ExecutionStatus'

interface ExecutionPanelProps {
  investigationId: string
  onExecute: (identifiers: Identifier[]) => void
}

export default function ExecutionPanel({ investigationId, onExecute }: ExecutionPanelProps) {
  const [identifiers, setIdentifiers] = useState<Identifier[]>([])
  const [executionStatus, setExecutionStatus] = useState<ExecutionStatusType>('not_started')
  const [isExecuting, setIsExecuting] = useState(false)

  const handleAddIdentifier = (value: string, type: IdentifierType) => {
    const newIdentifier: Identifier = {
      id: `id-${Date.now()}-${Math.random()}`,
      value,
      type,
      investigationId,
      addedAt: new Date().toISOString(),
    }
    setIdentifiers([...identifiers, newIdentifier])
  }

  const handleRemoveIdentifier = (id: string) => {
    setIdentifiers(identifiers.filter((i) => i.id !== id))
  }

  const handleExecute = () => {
    // Placeholder function - will be replaced with actual API call
    setIsExecuting(true)
    setExecutionStatus('running')

    // Simulate execution
    setTimeout(() => {
      setIsExecuting(false)
      setExecutionStatus('completed')
      onExecute(identifiers)
    }, 2000)
  }

  const getIdentifierTypeLabel = (type: IdentifierType): string => {
    const labels: Record<IdentifierType, string> = {
      email: 'Email',
      phone: 'Phone',
      username: 'Username',
      domain: 'Domain',
      wallet: 'Wallet',
      image: 'Image',
    }
    return labels[type]
  }

  return (
    <div className="space-y-6">
      <div className="rounded border border-line bg-surface p-6">
        <h3 className="text-base font-semibold text-text">Execute Investigation</h3>
        <p className="mt-1 text-sm text-muted">
          Add identifiers to investigate and execute the analysis
        </p>

        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          {/* Left: Add Identifiers */}
          <div>
            <h4 className="mb-4 text-sm font-medium text-text">Add Identifiers</h4>
            <IdentifierInput onAdd={handleAddIdentifier} disabled={isExecuting} />
          </div>

          {/* Right: Added Identifiers List */}
          <div>
            <h4 className="mb-4 text-sm font-medium text-text">
              Added Identifiers ({identifiers.length})
            </h4>
            {identifiers.length === 0 ? (
              <div className="rounded border border-dashed border-line bg-surface2 p-8 text-center">
                <p className="text-sm text-muted">No identifiers added yet</p>
              </div>
            ) : (
              <div className="space-y-2 max-h-[300px] overflow-y-auto rounded border border-line bg-surface2 p-3">
                {identifiers.map((identifier) => (
                  <div
                    key={identifier.id}
                    className="flex items-center justify-between rounded border border-line bg-surface px-3 py-2"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="rounded bg-surface2 px-2 py-0.5 font-mono text-[10px] uppercase tracking-tag text-faint">
                          {getIdentifierTypeLabel(identifier.type)}
                        </span>
                        <span className="truncate text-sm text-text">
                          {identifier.value}
                        </span>
                      </div>
                    </div>
                    <button
                      onClick={() => handleRemoveIdentifier(identifier.id)}
                      disabled={isExecuting}
                      className="ml-2 flex-shrink-0 text-muted transition-colors hover:text-danger disabled:cursor-not-allowed disabled:opacity-50"
                      aria-label="Remove identifier"
                    >
                      <svg
                        className="h-4 w-4"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M6 18L18 6M6 6l12 12"
                        />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Execute Button */}
        <div className="mt-6 border-t border-line pt-6">
          <button
            onClick={handleExecute}
            disabled={identifiers.length === 0 || isExecuting}
            className="w-full rounded border border-signal bg-signalDim px-6 py-3 text-sm font-semibold text-signal transition-colors hover:bg-signal/20 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-signal disabled:cursor-not-allowed disabled:opacity-50 md:w-auto"
          >
            {isExecuting ? 'Executing...' : 'Execute Investigation'}
          </button>
          <p className="mt-2 text-xs text-muted">
            This will query all relevant OSINT sources for the added identifiers
          </p>
        </div>
      </div>

      {/* Execution Status */}
      <ExecutionStatus status={executionStatus} />
    </div>
  )
}
