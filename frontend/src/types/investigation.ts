// Type definitions for Investigation domain
// Based on MASTER_DESIGN.md Section 11.9 (Investigation & Persistence Layer)

export type InvestigationStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface Investigation {
  id: string
  name: string
  createdAt: string
  status: InvestigationStatus
  identifierCount: number
  entityCount: number
  description?: string
}

export type IdentifierType = 'email' | 'phone' | 'username' | 'domain' | 'wallet' | 'image'

export interface Identifier {
  id: string
  value: string
  type: IdentifierType
  investigationId: string
  addedAt: string
}
