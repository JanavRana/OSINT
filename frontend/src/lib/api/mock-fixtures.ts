// Mock fixtures live behind the data-provider abstraction and are never
// imported directly by pages or components.
import type {
  Connector,
  DashboardStat,
  EvidenceEntry,
  GraphData,
  Identifier,
  IdentityProfile,
  Investigation,
  Report,
  TimelineEvent,
} from "@/types/domain";

export const investigationsFixture: Investigation[] = [
  { id: "INV-1042", name: "Operation Nightshade", target: "j.doe@protonmail.com", status: "active", severity: "critical", progress: 68, identifiers: 47, connectors: 12, createdAt: "2026-07-08T09:12:00Z", updatedAt: "2026-07-10T11:24:00Z", owner: "M. Chen", tags: ["phishing", "crypto"] },
  { id: "INV-1041", name: "Ghost Wallet Trace", target: "0x9a8b…f21c", status: "active", severity: "high", progress: 42, identifiers: 31, connectors: 8, createdAt: "2026-07-07T14:22:00Z", updatedAt: "2026-07-10T10:02:00Z", owner: "A. Rivera", tags: ["wallet", "chainalysis"] },
  { id: "INV-1040", name: "Domain Cluster Alpha", target: "secure-login-verify.io", status: "completed", severity: "high", progress: 100, identifiers: 82, connectors: 14, createdAt: "2026-07-05T08:00:00Z", updatedAt: "2026-07-09T18:40:00Z", owner: "L. Park", tags: ["domain", "typosquat"] },
  { id: "INV-1039", name: "Handle Cross-Ref", target: "@nullbyte_x", status: "pending", severity: "medium", progress: 12, identifiers: 6, connectors: 4, createdAt: "2026-07-09T22:11:00Z", updatedAt: "2026-07-10T02:00:00Z", owner: "M. Chen", tags: ["social"] },
  { id: "INV-1038", name: "Telegram Ring 42", target: "@ring42", status: "active", severity: "critical", progress: 55, identifiers: 63, connectors: 10, createdAt: "2026-07-04T12:00:00Z", updatedAt: "2026-07-10T09:15:00Z", owner: "S. Ito", tags: ["telegram", "fraud"] },
  { id: "INV-1037", name: "Breach Recovery — Acme", target: "acme.com", status: "completed", severity: "medium", progress: 100, identifiers: 128, connectors: 16, createdAt: "2026-06-28T09:00:00Z", updatedAt: "2026-07-06T19:00:00Z", owner: "A. Rivera", tags: ["breach", "credentials"] },
  { id: "INV-1036", name: "Failed Scrape — DarkForum", target: "onion:xyz…", status: "failed", severity: "low", progress: 22, identifiers: 3, connectors: 2, createdAt: "2026-07-01T10:00:00Z", updatedAt: "2026-07-02T10:00:00Z", owner: "L. Park", tags: ["darkweb"] },
  { id: "INV-1035", name: "APT-Q Attribution", target: "10.24.9.14", status: "active", severity: "high", progress: 74, identifiers: 55, connectors: 11, createdAt: "2026-06-30T10:00:00Z", updatedAt: "2026-07-10T08:00:00Z", owner: "S. Ito", tags: ["apt", "malware"] },
];

export const statsFixture: DashboardStat[] = [
  { label: "Active Investigations", value: 24, delta: "+3 this week", trend: "up", tone: "cyan" },
  { label: "Identifiers Enriched", value: "12,847", delta: "+1,204 24h", trend: "up", tone: "violet" },
  { label: "Connectors Online", value: "38 / 42", delta: "2 degraded", trend: "warn", tone: "warning" },
  { label: "Critical Alerts", value: 7, delta: "-2 today", trend: "down", tone: "danger" },
];

export const identifiersFixture: Identifier[] = [
  { id: "id1", type: "email", value: "j.doe@protonmail.com", confidence: 0.98, sources: 6, firstSeen: "2024-11-02" },
  { id: "id2", type: "email", value: "shadow.doe@tuta.io", confidence: 0.82, sources: 3, firstSeen: "2025-02-19" },
  { id: "id3", type: "domain", value: "secure-login-verify.io", confidence: 0.91, sources: 5, firstSeen: "2025-06-01" },
  { id: "id4", type: "username", value: "nullbyte_x", confidence: 0.76, sources: 4, firstSeen: "2024-09-11" },
  { id: "id5", type: "username", value: "j.doe_1990", confidence: 0.64, sources: 2, firstSeen: "2023-04-08" },
  { id: "id6", type: "wallet", value: "0x9a8b3f4c2d1e5f6a7b8c9d0e1f2a3b4c5d6e7f21c", confidence: 0.88, sources: 7, firstSeen: "2025-01-14" },
  { id: "id7", type: "social", value: "twitter.com/nullbyte_x", confidence: 0.79, sources: 3, firstSeen: "2024-09-12" },
  { id: "id8", type: "social", value: "t.me/ring42", confidence: 0.84, sources: 4, firstSeen: "2025-03-22" },
  { id: "id9", type: "phone", value: "+1 415 ••• 0142", confidence: 0.55, sources: 1, firstSeen: "2025-05-04" },
  { id: "id10", type: "ip", value: "185.220.101.47", confidence: 0.70, sources: 3, firstSeen: "2025-06-30" },
];

export const connectorsFixture: Connector[] = [
  { id: "c1", name: "HaveIBeenPwned", category: "Breach", status: "success", hits: 14, runtime: "1.2s" },
  { id: "c2", name: "Hunter.io", category: "Email", status: "success", hits: 8, runtime: "0.9s" },
  { id: "c3", name: "Shodan", category: "Network", status: "running", hits: 3, runtime: "…" },
  { id: "c4", name: "Whoxy WHOIS", category: "Domain", status: "success", hits: 22, runtime: "2.1s" },
  { id: "c5", name: "Chainalysis", category: "Crypto", status: "running", hits: 6, runtime: "…" },
  { id: "c6", name: "Twitter Graph", category: "Social", status: "queued", hits: 0, runtime: "—" },
  { id: "c7", name: "Telegram Scraper", category: "Social", status: "success", hits: 19, runtime: "4.4s" },
  { id: "c8", name: "GitHub Recon", category: "Code", status: "failed", hits: 0, runtime: "0.3s" },
  { id: "c9", name: "VirusTotal", category: "Malware", status: "success", hits: 5, runtime: "0.7s" },
  { id: "c10", name: "MaxMind GeoIP", category: "Network", status: "success", hits: 11, runtime: "0.4s" },
  { id: "c11", name: "Etherscan", category: "Crypto", status: "success", hits: 9, runtime: "1.0s" },
  { id: "c12", name: "IntelX", category: "Dark Web", status: "queued", hits: 0, runtime: "—" },
];

export const timelineFixture: TimelineEvent[] = [
  { id: "t1", time: "2026-07-10T11:24:00Z", actor: "Chainalysis", action: "Flagged", target: "0x9a8b…f21c", channel: "wallet", severity: "critical", details: "Mixer interaction — Tornado Cash outflow observed." },
  { id: "t2", time: "2026-07-10T10:12:00Z", actor: "Shodan", action: "Discovered", target: "185.220.101.47:22", channel: "network", severity: "high", details: "Tor exit relay hosting SSH on port 22." },
  { id: "t3", time: "2026-07-10T08:44:00Z", actor: "Telegram Scraper", action: "Captured", target: "@ring42", channel: "social", severity: "high", details: "New message referencing target email in channel." },
  { id: "t4", time: "2026-07-09T22:03:00Z", actor: "HaveIBeenPwned", action: "Match", target: "j.doe@protonmail.com", channel: "email", severity: "medium", details: "Present in 6 breach datasets (2019–2024)." },
  { id: "t5", time: "2026-07-09T15:28:00Z", actor: "Whoxy", action: "Registered", target: "secure-login-verify.io", channel: "domain", severity: "high", details: "Registered via NameSilo, privacy-protected, 3 days old." },
  { id: "t6", time: "2026-07-08T09:12:00Z", actor: "M. Chen", action: "Created", target: "Investigation INV-1042", channel: "system", severity: "low", details: "Investigation opened, seed identifier attached." },
];

export const reportsFixture: Report[] = [
  { id: "r1", name: "Nightshade — Executive Summary", investigation: "INV-1042", createdAt: "2026-07-10", pages: 12, format: "PDF", size: "2.4 MB" },
  { id: "r2", name: "Nightshade — Full Evidence Pack", investigation: "INV-1042", createdAt: "2026-07-10", pages: 84, format: "PDF", size: "14.1 MB" },
  { id: "r3", name: "Ghost Wallet — Chain Analysis", investigation: "INV-1041", createdAt: "2026-07-09", pages: 22, format: "PDF", size: "3.8 MB" },
  { id: "r4", name: "Domain Cluster Alpha — Final", investigation: "INV-1040", createdAt: "2026-07-08", pages: 46, format: "PDF", size: "6.7 MB" },
  { id: "r5", name: "APT-Q — IOC Export", investigation: "INV-1035", createdAt: "2026-07-07", pages: 0, format: "JSON", size: "412 KB" },
];

const evidenceFixture: EvidenceEntry[] = [
  { src: "HaveIBeenPwned", finding: "6 breach matches for j.doe@protonmail.com", conf: 0.98 },
  { src: "Etherscan", finding: "Wallet 0x9a8b…f21c received 0.42 ETH from mixer", conf: 0.92 },
  { src: "Whoxy", finding: "Domain secure-login-verify.io registered with same phone hash", conf: 0.84 },
  { src: "Twitter Graph", finding: "@nullbyte_x bio contains proton email pattern", conf: 0.71 },
];

export const identityProfileFixture: IdentityProfile = {
  subjectId: "SUBJECT-a29fc41e",
  displayName: "John Doe (attributed)",
  initials: "JD",
  linkedInvestigation: "INV-1042",
  totalIdentifiers: 47,
  totalSources: 12,
  overallConfidence: 0.86,
  evidence: evidenceFixture,
  sections: [
    { key: "emails", title: "Emails", items: [
      { value: "j.doe@protonmail.com", confidence: 0.98, sources: 6, note: "Primary — active" },
      { value: "shadow.doe@tuta.io", confidence: 0.82, sources: 3, note: "Alias" },
      { value: "jd1990@gmail.com", confidence: 0.61, sources: 2, note: "Historical" },
    ]},
    { key: "domains", title: "Domains", items: [
      { value: "secure-login-verify.io", confidence: 0.91, sources: 5, note: "Typosquat" },
      { value: "doe-consulting.net", confidence: 0.74, sources: 3, note: "Personal" },
    ]},
    { key: "usernames", title: "Usernames", items: [
      { value: "nullbyte_x", confidence: 0.76, sources: 4, note: "Twitter / GitHub" },
      { value: "j.doe_1990", confidence: 0.64, sources: 2, note: "Reddit" },
      { value: "jdoe", confidence: 0.48, sources: 1, note: "Steam" },
    ]},
    { key: "wallets", title: "Wallets", items: [
      { value: "0x9a8b3f4c2d1e5f6a7b8c9d0e1f2a3b4c5d6e7f21c", confidence: 0.88, sources: 7, note: "Ethereum" },
      { value: "bc1q…9v3f", confidence: 0.55, sources: 1, note: "Bitcoin — unverified" },
    ]},
    { key: "social", title: "Social Accounts", items: [
      { value: "twitter.com/nullbyte_x", confidence: 0.79, sources: 3, note: "2.1k followers" },
      { value: "t.me/ring42", confidence: 0.84, sources: 4, note: "Channel admin" },
      { value: "github.com/nullbyte", confidence: 0.66, sources: 2, note: "12 repos" },
    ]},
    { key: "phones", title: "Phones", items: [
      { value: "+1 415 ••• 0142", confidence: 0.55, sources: 1, note: "SF Bay Area" },
    ]},
    { key: "network", title: "Network", items: [
      { value: "185.220.101.47", confidence: 0.70, sources: 3, note: "Tor exit" },
      { value: "AS14061 — DigitalOcean", confidence: 0.62, sources: 2, note: "Recent" },
    ]},
  ],
};

export const graphFixture: GraphData = {
  nodes: [
    { id: "n1", label: "j.doe@protonmail.com", type: "email", x: 50, y: 45, primary: true, size: 34 },
    { id: "n2", label: "nullbyte_x", type: "user", x: 25, y: 25 },
    { id: "n3", label: "secure-login-verify.io", type: "domain", x: 75, y: 30 },
    { id: "n4", label: "0x9a8b…f21c", type: "wallet", x: 78, y: 65 },
    { id: "n5", label: "185.220.101.47", type: "ip", x: 25, y: 68 },
    { id: "n6", label: "shadow.doe@tuta.io", type: "email", x: 15, y: 48 },
    { id: "n7", label: "t.me/ring42", type: "user", x: 88, y: 48 },
    { id: "n8", label: "j.doe_1990", type: "user", x: 35, y: 82 },
    { id: "n9", label: "acme.com", type: "domain", x: 62, y: 15 },
  ],
  edges: [
    { from: "n1", to: "n2", kind: "handle" },
    { from: "n1", to: "n3", kind: "domain-match" },
    { from: "n1", to: "n4", kind: "wallet-link" },
    { from: "n1", to: "n5", kind: "session-ip" },
    { from: "n1", to: "n6", kind: "alias" },
    { from: "n3", to: "n9", kind: "typosquat" },
    { from: "n4", to: "n7", kind: "mention" },
    { from: "n2", to: "n8", kind: "aka" },
    { from: "n5", to: "n8", kind: "session-ip" },
  ],
};
