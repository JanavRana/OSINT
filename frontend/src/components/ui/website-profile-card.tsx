import { useState } from "react";
import { ExternalLink, Globe, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import { ConfidenceBar } from "@/components/confidence-bar";

// ── URL parsing ───────────────────────────────────────────────────────────────

export function parseUrl(raw: string): {
  href: string;
  domain: string;
  handle: string | null;
} {
  let href = raw;
  if (!/^https?:\/\//i.test(raw)) href = `https://${raw}`;
  let domain = raw;
  let handle: string | null = null;
  try {
    const url = new URL(href);
    domain = url.hostname.replace(/^www\./, "");
    const segments = url.pathname.split("/").filter(Boolean);
    if (segments.length > 0) handle = segments[0];
  } catch {
    domain = raw.replace(/^www\./, "").split("/")[0];
  }
  return { href, domain, handle };
}

// ── Platform brand registry ───────────────────────────────────────────────────

export interface PlatformBrand {
  name: string;
  accent: string;
  bg: string; // banner background gradient/color
}

export const PLATFORM_BRANDS: Record<string, PlatformBrand> = {
  "github.com":        { name: "GitHub",         accent: "#6e40c9", bg: "linear-gradient(135deg, #161b22 0%, #1c1f26 100%)" },
  "twitter.com":       { name: "Twitter / X",    accent: "#1d9bf0", bg: "linear-gradient(135deg, #0a0f14 0%, #0d1825 100%)" },
  "x.com":             { name: "Twitter / X",    accent: "#1d9bf0", bg: "linear-gradient(135deg, #0a0f14 0%, #0d1825 100%)" },
  "linkedin.com":      { name: "LinkedIn",        accent: "#0a66c2", bg: "linear-gradient(135deg, #071825 0%, #0a1f31 100%)" },
  "spotify.com":       { name: "Spotify",         accent: "#1db954", bg: "linear-gradient(135deg, #0d1a0f 0%, #111f14 100%)" },
  "instagram.com":     { name: "Instagram",       accent: "#e1306c", bg: "linear-gradient(135deg, #1a0a10 0%, #1f0e18 100%)" },
  "facebook.com":      { name: "Facebook",        accent: "#1877f2", bg: "linear-gradient(135deg, #07101e 0%, #0a1428 100%)" },
  "reddit.com":        { name: "Reddit",          accent: "#ff4500", bg: "linear-gradient(135deg, #1a0d00 0%, #1f1007 100%)" },
  "discord.com":       { name: "Discord",         accent: "#5865f2", bg: "linear-gradient(135deg, #0d0f1a 0%, #12152b 100%)" },
  "youtube.com":       { name: "YouTube",         accent: "#ff0000", bg: "linear-gradient(135deg, #1a0000 0%, #1f0505 100%)" },
  "tiktok.com":        { name: "TikTok",          accent: "#69c9d0", bg: "linear-gradient(135deg, #0a1214 0%, #0d1a1c 100%)" },
  "telegram.org":      { name: "Telegram",        accent: "#26a5e4", bg: "linear-gradient(135deg, #061520 0%, #081c2b 100%)" },
  "t.me":              { name: "Telegram",        accent: "#26a5e4", bg: "linear-gradient(135deg, #061520 0%, #081c2b 100%)" },
  "twitch.tv":         { name: "Twitch",          accent: "#9146ff", bg: "linear-gradient(135deg, #0f0a1a 0%, #150e26 100%)" },
  "pinterest.com":     { name: "Pinterest",       accent: "#e60023", bg: "linear-gradient(135deg, #1a0004 0%, #1f0008 100%)" },
  "medium.com":        { name: "Medium",          accent: "#00ab6c", bg: "linear-gradient(135deg, #001a10 0%, #001f14 100%)" },
  "stackoverflow.com": { name: "Stack Overflow",  accent: "#f48024", bg: "linear-gradient(135deg, #1a0e00 0%, #1f1200 100%)" },
  "gitlab.com":        { name: "GitLab",          accent: "#fc6d26", bg: "linear-gradient(135deg, #1a0e04 0%, #1f1208 100%)" },
  "gravatar.com":      { name: "Gravatar",        accent: "#1e8cbf", bg: "linear-gradient(135deg, #06121a 0%, #081820 100%)" },
  "patreon.com":       { name: "Patreon",         accent: "#ff424d", bg: "linear-gradient(135deg, #1a0607 0%, #1f0a0b 100%)" },
  "paypal.com":        { name: "PayPal",          accent: "#003087", bg: "linear-gradient(135deg, #000a1a 0%, #000d21 100%)" },
  "steam":             { name: "Steam",           accent: "#66c0f4", bg: "linear-gradient(135deg, #0a1520 0%, #0e1f30 100%)" },
};

export function getBrand(domain: string): PlatformBrand | null {
  if (PLATFORM_BRANDS[domain]) return PLATFORM_BRANDS[domain];
  const parts = domain.split(".");
  if (parts.length > 2) {
    const root = parts.slice(-2).join(".");
    if (PLATFORM_BRANDS[root]) return PLATFORM_BRANDS[root];
  }
  return null;
}

// ── Platform Logo Avatar ─────────────────────────────────────────────────────

function PlatformLogoAvatar({
  domain,
  accentColor,
  size = 42,
  fallbackIcon: FallbackIcon = Globe,
}: {
  domain: string;
  accentColor: string;
  size?: number;
  fallbackIcon?: typeof Globe;
}) {
  const [errored, setErrored] = useState(false);

  return (
    <div
      className="rounded-full border-2 grid place-items-center shrink-0 bg-surface-3 overflow-hidden p-2"
      style={{
        width: size,
        height: size,
        borderColor: `${accentColor}80`,
        boxShadow: `0 0 10px ${accentColor}40`,
      }}
      aria-hidden="true"
    >
      {!errored ? (
        <img
          src={`https://www.google.com/s2/favicons?domain=${domain}&sz=64`}
          alt=""
          className="w-full h-full object-contain"
          onError={() => setErrored(true)}
        />
      ) : (
        <FallbackIcon className="w-1/2 h-1/2 text-muted-foreground" />
      )}
    </div>
  );
}

// ── Favicon ───────────────────────────────────────────────────────────────────

function Favicon({ domain, size = 14 }: { domain: string; size?: number }) {
  const [errored, setErrored] = useState(false);
  if (errored) {
    return <Globe style={{ width: size, height: size }} className="text-muted-foreground shrink-0" aria-hidden="true" />;
  }
  return (
    <img
      src={`https://www.google.com/s2/favicons?domain=${domain}&sz=64`}
      alt=""
      aria-hidden="true"
      style={{ width: size, height: size }}
      className="rounded-sm shrink-0 object-contain"
      onError={() => setErrored(true)}
    />
  );
}

// ── ReconstructedProfileCard ──────────────────────────────────────────────────

export interface ReconstructedProfileCardProps {
  /** Raw profile URL, e.g. "https://github.com/janavrana" */
  url: string;
  /** Confidence value (0-1 or 0-100, same scale as ConfidenceBar) */
  confidence?: number;
  /** Platform display name override (e.g. from identifier.platformDisplayName) */
  platformDisplayName?: string;
  className?: string;
  id?: string;
}

export function ReconstructedProfileCard({
  url,
  confidence,
  platformDisplayName,
  className,
  id,
}: ReconstructedProfileCardProps) {
  const { href, domain, handle } = parseUrl(url);
  const brand = getBrand(domain);
  const displayName = platformDisplayName ?? brand?.name ?? domain;
  const accentColor = brand?.accent ?? "#6b7280";
  const bannerBg = brand?.bg ?? "linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)";

  return (
    <div
      id={id}
      className={cn(
        "rounded-md border bg-surface-2/80 backdrop-blur-sm overflow-hidden",
        "transition-all duration-200 hover:border-primary/50",
        className
      )}
      style={{
        borderLeftColor: accentColor,
        borderLeftWidth: "3px",
        borderColor: `${accentColor}40`,
        background: `linear-gradient(135deg, ${accentColor}12 0%, rgba(20, 24, 33, 0.85) 100%)`,
        boxShadow: `0 4px 20px -5px ${accentColor}25, inset 0 0 30px -5px ${accentColor}18`,
      }}
    >
      {/* Platform brand banner */}
      <div
        className="h-12 w-full relative flex items-center px-3"
        style={{ background: bannerBg }}
        aria-hidden="true"
      >
        {/* Diagonal stripe overlay */}
        <div
          className="absolute inset-0"
          style={{
            backgroundImage: `repeating-linear-gradient(45deg, ${accentColor}08 0px, ${accentColor}08 1px, transparent 1px, transparent 8px)`,
          }}
        />
        {/* Platform name — prominent left-aligned */}
        <span
          className="relative text-[11px] font-mono font-bold uppercase tracking-widest"
          style={{ color: accentColor }}
        >
          {displayName}
        </span>
        {/* Accent glow strip at bottom */}
        <div
          className="absolute bottom-0 left-0 right-0 h-px"
          style={{ background: `linear-gradient(90deg, ${accentColor}90, transparent)` }}
        />
      </div>

      {/* Card body */}
      <div className="px-3 pt-0 pb-3">
        {/* Platform logo avatar — overlaps banner */}
        <div className="flex items-end gap-2.5 -mt-5 mb-2">
          <PlatformLogoAvatar
            domain={domain}
            accentColor={accentColor}
            size={42}
          />
          <div className="min-w-0 pb-0.5">
            <span
              className="text-[10px] font-mono truncate block"
              style={{ color: `${accentColor}cc` }}
            >
              {domain}
            </span>
          </div>
        </div>

        {/* Handle + OSINT badge */}
        <div className="flex items-center gap-2 mb-1.5">
          <span className="text-sm font-bold font-mono text-foreground truncate">
            {handle ? `@${handle}` : domain}
          </span>
          <span
            className="inline-flex items-center gap-0.5 text-[9px] font-mono font-bold uppercase px-1.5 py-0.5 rounded-sm border shrink-0"
            style={{
              color: accentColor,
              borderColor: `${accentColor}40`,
              background: `${accentColor}15`,
              boxShadow: `0 0 8px ${accentColor}50`,
            }}
          >
            <ShieldCheck className="h-2.5 w-2.5" aria-hidden="true" />
            OSINT HIT
          </span>
        </div>

        {/* Confidence bar */}
        {confidence !== undefined && (
          <div className="mb-2.5">
            <ConfidenceBar
              value={confidence}
              ariaLabel={`Confidence for ${handle ?? domain}`}
            />
          </div>
        )}

        {/* Open native profile button */}
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={`Open ${displayName} profile for ${handle ?? domain} in new tab`}
          className={cn(
            "group w-full inline-flex items-center justify-center gap-1.5 rounded-sm border px-2.5 py-1",
            "text-[10px] font-mono font-semibold uppercase tracking-wider transition-all duration-200",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          )}
          style={{
            color: accentColor,
            borderColor: `${accentColor}50`,
            background: `${accentColor}10`,
          }}
        >
          <ExternalLink className="h-2.5 w-2.5 shrink-0" aria-hidden="true" />
          Open Native Profile
        </a>
      </div>
    </div>
  );
}

// ── WebsiteProfileCard (small card — kept for identity.tsx compat) ─────────────

export interface WebsiteProfileCardProps {
  url: string;
  confidence?: number;
  platformDisplayName?: string;
  className?: string;
  id?: string;
}

/** Alias: renders the full ReconstructedProfileCard */
export function WebsiteProfileCard(props: WebsiteProfileCardProps) {
  return <ReconstructedProfileCard {...props} />;
}

// ── WebsiteIdentifierBadge (inline pill for table cells) ──────────────────────

export interface WebsiteIdentifierBadgeProps {
  url: string;
  className?: string;
  id?: string;
}

export function WebsiteIdentifierBadge({ url, className, id }: WebsiteIdentifierBadgeProps) {
  const { href, domain, handle } = parseUrl(url);
  const brand = getBrand(domain);
  const label = handle ? `@${handle}` : domain;

  return (
    <a
      id={id}
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={`Open ${brand?.name ?? domain}${handle ? ` @${handle}` : ""} in new tab`}
      className={cn(
        "group inline-flex items-center gap-1.5 rounded-sm border border-border/60 bg-surface-2/80",
        "px-2 py-0.5 text-[10px] font-mono transition-all duration-200",
        "hover:border-primary/50 hover:bg-surface-3",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        className
      )}
      style={brand?.accent ? { borderLeftColor: brand.accent, borderLeftWidth: "2px" } : undefined}
    >
      <Favicon domain={domain} size={11} />
      <span className="truncate max-w-[120px] text-foreground" title={label}>{label}</span>
      <ExternalLink className="h-2.5 w-2.5 shrink-0 text-muted-foreground group-hover:text-primary transition-colors" aria-hidden="true" />
    </a>
  );
}
