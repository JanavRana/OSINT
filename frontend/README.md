# OSINT Aggregator — Frontend Skeleton

Vite + React + TypeScript + Tailwind skeleton for the Advanced Multi-Platform
OSINT Intelligence Aggregator (see `MASTER_DESIGN.md` in the project root).

## Scope of this skeleton

Included:
- Vite/React/TS project setup
- Tailwind configuration with the platform's design tokens
- React Router with a persistent sidebar layout
- Five placeholder pages: Dashboard, Investigations, Graph, Timeline, Reports

Deliberately **not** included (left for later, module-scoped work):
- API calls / data fetching
- Graph visualization (Cytoscape.js) — M5
- Timeline rendering logic — M7
- Authentication — NFR10
- State management
- Any business logic

## Getting started

```bash
npm install
npm run dev
```

## Structure

```
src/
├── layout/
│   ├── AppLayout.tsx     # shell: sidebar + routed content
│   ├── Sidebar.tsx       # nav, driven by theme/navigation.ts
│   └── PageHeader.tsx    # shared placeholder page header
├── pages/
│   ├── Dashboard.tsx
│   ├── Investigations.tsx
│   ├── Graph.tsx
│   ├── Timeline.tsx
│   └── Reports.tsx
├── theme/
│   └── navigation.ts     # nav manifest (route + index code)
├── App.tsx               # router setup
├── main.tsx              # React entry point
└── index.css             # Tailwind directives + base theme
```
