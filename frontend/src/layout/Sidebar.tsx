import { NavLink } from 'react-router-dom'
import { NAV_ENTRIES } from '../theme/navigation'

export default function Sidebar() {
  return (
    <aside className="flex h-screen w-64 shrink-0 flex-col border-r border-line bg-surface">
      <div className="border-b border-line px-6 py-6">
        <p className="font-mono text-[11px] uppercase tracking-tag text-faint">
          Case Platform
        </p>
        <h1 className="mt-1 font-mono text-sm font-semibold text-text">
          OSINT Aggregator
        </h1>
      </div>

      <nav className="flex-1 overflow-y-auto py-4">
        <ul className="flex flex-col gap-1 px-3">
          {NAV_ENTRIES.map((entry) => (
            <li key={entry.path}>
              <NavLink
                to={entry.path}
                end={entry.path === '/'}
                className={({ isActive }) =>
                  [
                    'group flex items-center gap-3 rounded-sm border-l-2 px-3 py-2.5 transition-colors',
                    isActive
                      ? 'border-signal bg-signalDim/40 text-text'
                      : 'border-transparent text-muted hover:border-line hover:bg-surface2 hover:text-text',
                  ].join(' ')
                }
              >
                {({ isActive }) => (
                  <>
                    <span
                      className={[
                        'font-mono text-[11px] tabular-nums',
                        isActive ? 'text-signal' : 'text-faint group-hover:text-muted',
                      ].join(' ')}
                    >
                      {entry.index}
                    </span>
                    <span className="text-sm">{entry.label}</span>
                  </>
                )}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      <div className="border-t border-line px-6 py-4">
        <p className="font-mono text-[11px] text-faint">v1 · local-first</p>
      </div>
    </aside>
  )
}
