import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { Investigation, Identifier } from '../types/investigation'
import InvestigationHeader from '../components/InvestigationHeader'
import ExecutionPanel from '../components/ExecutionPanel'

// Mock data for demonstration
const MOCK_INVESTIGATION: Investigation = {
  id: 'inv-2026-001',
  name: 'Case 2026-0417',
  createdAt: '2026-07-11T10:30:00Z',
  status: 'pending',
  identifierCount: 0,
  entityCount: 0,
  description: 'Investigation of suspicious email activity related to phishing campaign',
}

export default function InvestigationDetails() {
  // TODO: Use id from params to fetch investigation from API
  // const { id } = useParams<{ id: string }>()
  
  const navigate = useNavigate()
  const [investigation, setInvestigation] = useState<Investigation>(MOCK_INVESTIGATION)

  // Placeholder function for execution
  // TODO: Replace with actual API call to backend
  const handleExecuteInvestigation = (identifiers: Identifier[]) => {
    console.log('Execute investigation with identifiers:', identifiers)
    
    // Update mock investigation state
    setInvestigation({
      ...investigation,
      identifierCount: identifiers.length,
      status: 'running',
    })

    // TODO: Make API call to POST /investigations/{id}/identifiers
    // TODO: Poll GET /investigations/{id}/status for progress
    // TODO: Update investigation state based on response
  }

  const handleBack = () => {
    navigate('/investigations')
  }

  return (
    <div>
      {/* Back Navigation */}
      <button
        onClick={handleBack}
        className="mb-6 flex items-center gap-2 text-sm text-muted transition-colors hover:text-text"
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
            d="M15 19l-7-7 7-7"
          />
        </svg>
        Back to Investigations
      </button>

      {/* Investigation Header */}
      <InvestigationHeader investigation={investigation} />

      {/* Execution Panel */}
      <ExecutionPanel
        investigationId={investigation.id}
        onExecute={handleExecuteInvestigation}
      />

      {/* Placeholder sections for future implementation */}
      <div className="mt-8 space-y-4">
        <div className="rounded border border-dashed border-line bg-scan p-6 text-center">
          <p className="font-mono text-[11px] uppercase tracking-tag text-faint">
            Coming Soon
          </p>
          <p className="mt-2 text-sm text-muted">
            Graph visualization, timeline, and entity profiles will appear here after execution
          </p>
        </div>
      </div>
    </div>
  )
}
