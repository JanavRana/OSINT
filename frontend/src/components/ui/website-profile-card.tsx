import { useState } from "react";
import { ExternalLink, Globe, Mail, Phone, Server, User, Wallet } from "lucide-react";
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
  "hackerrank.com":    { name: "HackerRank",      accent: "#2ec4b6", bg: "linear-gradient(135deg, #051b18 0%, #082924 100%)" },
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

export function isIpAddress(val: string): boolean {
  if (!val) return false;
  const clean = val.trim();
  if (/^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(clean)) return true;
  if (clean.includes(":") && /^[0-9a-fA-F:]+$/.test(clean)) return true;
  return false;
}

export function getTypeAccent(type?: string, platformDisplayName?: string): string {
  const pName = platformDisplayName?.toLowerCase() || "";
  if (pName.includes("mail server") || pName.includes("mx")) {
    return "#3b82f6";
  }
  if (pName.includes("resolved ip") || pName.includes("ip address") || type === "ip" || type === "mac") {
    return "#ef4444";
  }
  switch (type) {
    case "email": return "#3b82f6";
    case "domain": return "#06b6d4";
    case "username":
    case "social": return "#f59e0b";
    case "wallet": return "#10b981";
    case "phone": return "#8b5cf6";
    case "ip":
    case "mac": return "#ef4444";
    default: return "#06b6d4";
  }
}

export function getTypeBannerBg(type?: string, platformDisplayName?: string): string {
  const pName = platformDisplayName?.toLowerCase() || "";
  if (pName.includes("mail server") || pName.includes("mx")) {
    return "linear-gradient(135deg, #0b192e 0%, #0d2240 100%)";
  }
  if (pName.includes("resolved ip") || pName.includes("ip address") || type === "ip" || type === "mac") {
    return "linear-gradient(135deg, #290808 0%, #380a0a 100%)";
  }
  switch (type) {
    case "email": return "linear-gradient(135deg, #0b192e 0%, #0d2240 100%)";
    case "domain": return "linear-gradient(135deg, #081d24 0%, #0a2933 100%)";
    case "username":
    case "social": return "linear-gradient(135deg, #241908 0%, #33230a 100%)";
    case "wallet": return "linear-gradient(135deg, #082419 0%, #0a3323 100%)";
    case "phone": return "linear-gradient(135deg, #180b2e 0%, #220d40 100%)";
    case "ip":
    case "mac": return "linear-gradient(135deg, #290808 0%, #380a0a 100%)";
    default: return "linear-gradient(135deg, #10141e 0%, #171d2b 100%)";
  }
}

function getTypeIcon(type?: string, platformDisplayName?: string) {
  const pName = platformDisplayName?.toLowerCase() || "";
  if (pName.includes("mail server") || pName.includes("mx")) {
    return Mail;
  }
  if (pName.includes("resolved ip") || pName.includes("ip address") || type === "ip" || type === "mac") {
    return Server;
  }
  switch (type) {
    case "email": return Mail;
    case "domain": return Globe;
    case "username":
    case "social": return User;
    case "wallet": return Wallet;
    case "phone": return Phone;
    case "ip":
    case "mac": return Server;
    default: return Globe;
  }
}

// ── Platform Logo Avatar ─────────────────────────────────────────────────────

function PlatformLogoAvatar({
  domain,
  type,
  platformDisplayName,
  accentColor,
  size = 44,
}: {
  domain?: string | null;
  type?: string;
  platformDisplayName?: string;
  accentColor: string;
  size?: number;
}) {
  const [errored, setErrored] = useState(false);
  const isKnownBrand = domain ? Boolean(getBrand(domain) || PLATFORM_BRANDS[domain]) : false;
  const SymbolIcon = getTypeIcon(type, platformDisplayName);

  return (
    <div
      className="rounded-full border-2 grid place-items-center shrink-0 shadow-lg overflow-hidden p-1.5 relative z-10"
      style={{
        width: size,
        height: size,
        borderColor: `${accentColor}aa`,
        boxShadow: `0 0 12px ${accentColor}40`,
        background: `linear-gradient(135deg, ${accentColor}25 0%, #0d1117 100%)`,
      }}
      aria-hidden="true"
    >
      {isKnownBrand && !errored ? (
        <img
          src={`https://www.google.com/s2/favicons?domain=${domain}&sz=64`}
          alt=""
          className="w-full h-full object-contain"
          onError={() => setErrored(true)}
        />
      ) : (
        <SymbolIcon className="w-5 h-5 shrink-0" style={{ color: accentColor }} />
      )}
    </div>
  );
}

// ── Favicon ───────────────────────────────────────────────────────────────────

function Favicon({ domain, size = 14 }: { domain: string; size?: number }) {
  const [errored, setErrored] = useState(false);
  const isKnownBrand = domain ? Boolean(getBrand(domain) || PLATFORM_BRANDS[domain]) : false;
  if (!isKnownBrand || errored) {
    return null;
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
  /** Raw profile URL or value */
  url?: string;
  value?: string;
  type?: string;
  /** Confidence value (0-1 or 0-100, same scale as ConfidenceBar) */
  confidence?: number;
  /** Platform display name override (e.g. from identifier.platformDisplayName) */
  platformDisplayName?: string;
  profileUrl?: string;
  className?: string;
  id?: string;
}

export function ReconstructedProfileCard({
  url,
  value,
  type,
  confidence,
  platformDisplayName,
  profileUrl,
  className,
  id,
}: ReconstructedProfileCardProps) {
  const targetUrl = profileUrl || (url && url.includes(".") && !isIpAddress(url) ? url : undefined);
  
  let href: string | undefined = undefined;
  let domain: string | undefined = undefined;
  let handle: string | null = null;

  if (targetUrl) {
    const parsed = parseUrl(targetUrl);
    href = parsed.href;
    domain = parsed.domain;
    handle = parsed.handle;
  }

  if (!domain && value && !isIpAddress(value)) {
    if (value.includes("@")) {
      const parts = value.split("@");
      if (parts.length > 1 && parts[1].includes(".")) domain = parts[1];
    } else if (
      value.includes(".") &&
      !value.startsWith("Yes") &&
      !value.startsWith("No") &&
      !isIpAddress(value)
    ) {
      const parsed = parseUrl(value);
      domain = parsed.domain;
      if (!href) href = parsed.href;
    }
  }

  if (domain && isIpAddress(domain)) {
    domain = undefined;
  }

  const brand = domain ? getBrand(domain) : null;
  const accentColor = brand?.accent ?? getTypeAccent(type, platformDisplayName);
  const bannerBg = brand?.bg ?? getTypeBannerBg(type, platformDisplayName);
  const displayName = platformDisplayName ?? brand?.name ?? (type ? type.toUpperCase() : (domain || "IDENTIFIER"));
  const displayValue = handle ? `@${handle}` : (value || domain || url || "");
  const FallbackIcon = getTypeIcon(type, platformDisplayName);

  return (
    <div
      id={id}
      className={cn(
        "rounded-md border bg-surface-2/80 backdrop-blur-sm overflow-hidden flex flex-col justify-between min-h-[145px]",
        "transition-all duration-200 hover:border-primary/50 hover:shadow-lg",
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
        className="h-12 w-full relative flex items-center justify-end px-3 shrink-0"
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

        {/* Platform name — right aligned pill to keep space clear for avatar logo on left */}
        <span
          className="relative z-0 text-[10px] font-mono font-bold uppercase tracking-widest px-2 py-0.5 rounded-sm border truncate max-w-[170px]"
          style={{
            color: accentColor,
            borderColor: `${accentColor}40`,
            background: "rgba(10, 14, 23, 0.75)",
            backdropFilter: "blur(4px)",
          }}
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
      <div className="px-3 pt-0 pb-3 flex flex-col justify-between flex-1">
        <div>
          {/* Platform logo avatar — overlaps banner cleanly without cutoff */}
          <div className="flex items-end gap-2.5 -mt-6 mb-2">
            <PlatformLogoAvatar
              domain={domain}
              type={type}
              platformDisplayName={platformDisplayName}
              accentColor={accentColor}
              size={44}
            />
            {domain && (
              <div className="min-w-0 pb-0.5">
                <span
                  className="text-[10px] font-mono truncate block"
                  style={{ color: `${accentColor}dd` }}
                >
                  {domain}
                </span>
              </div>
            )}
          </div>

          {/* Main Handle / Identifier Value */}
          <div className="mb-2">
            <span className="text-sm font-bold font-mono text-foreground truncate block" title={displayValue}>
              {displayValue}
            </span>
          </div>
        </div>

        <div>
          {/* Confidence bar */}
          {confidence !== undefined && (
            <div className="mb-2.5">
              <ConfidenceBar
                value={confidence}
                ariaLabel={`Confidence for ${displayValue}`}
              />
            </div>
          )}

          {/* Open native profile button */}
          {href && (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={`Open ${displayName} profile for ${displayValue} in new tab`}
              className={cn(
                "group w-full inline-flex items-center justify-center gap-1.5 rounded-sm border px-2.5 py-1.5",
                "text-[10px] font-mono font-semibold uppercase tracking-wider transition-all duration-200",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              )}
              style={{
                color: accentColor,
                borderColor: `${accentColor}50`,
                background: `${accentColor}12`,
              }}
            >
              <ExternalLink className="h-3 w-3 shrink-0" aria-hidden="true" />
              Open Native Profile
            </a>
          )}
        </div>
      </div>
    </div>
  );
}

// ── WebsiteProfileCard (alias for compatibility) ──────────────────────────────

export interface WebsiteProfileCardProps {
  url?: string;
  value?: string;
  type?: string;
  confidence?: number;
  platformDisplayName?: string;
  profileUrl?: string;
  className?: string;
  id?: string;
}

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

