import type { Config } from 'tailwindcss'

// Design tokens for the OSINT Intelligence Aggregator.
// Palette reads as case-file / forensic tooling: near-black ground,
// a single teal "signal" accent for anything actionable or confirmed,
// and amber reserved strictly for confidence/attention states.
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#0B0F14',       // page background
        surface: '#121822',    // panels, sidebar
        surface2: '#1A2331',   // raised cards, hovers
        line: '#232E3D',       // borders / dividers
        text: '#E6EDF3',       // primary text
        muted: '#8B98A8',      // secondary text
        faint: '#5B6675',      // tertiary / disabled text
        signal: '#4FD1C5',     // teal accent — active state, links, evidence traces
        signalDim: '#1F4B48',  // teal used as a subtle background tint
        amber: '#E8B84B',      // confidence / attention
        danger: '#E5534B',     // errors, failed connectors
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      letterSpacing: {
        tag: '0.14em',
      },
      backgroundImage: {
        scan: 'repeating-linear-gradient(180deg, rgba(255,255,255,0.015) 0px, rgba(255,255,255,0.015) 1px, transparent 1px, transparent 3px)',
      },
    },
  },
  plugins: [],
} satisfies Config
