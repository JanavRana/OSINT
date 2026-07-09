// Static navigation manifest for the app shell.
// Each entry carries a two-digit "index code" — the sidebar's signature
// device, borrowed from case-file tab indexing — plus the route it maps to.
// No data or business logic lives here, only display metadata.

export interface NavEntry {
  index: string
  label: string
  path: string
}

export const NAV_ENTRIES: NavEntry[] = [
  { index: '00', label: 'Dashboard', path: '/' },
  { index: '01', label: 'Investigations', path: '/investigations' },
  { index: '02', label: 'Graph', path: '/graph' },
  { index: '03', label: 'Timeline', path: '/timeline' },
  { index: '04', label: 'Reports', path: '/reports' },
]
