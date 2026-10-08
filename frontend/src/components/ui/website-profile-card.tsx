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
  bg: string;
}

export const PLATFORM_BRANDS: Record<string, PlatformBrand> = {
  "github.com":        { name: "GitHub",         accent: "#8b5cf6", bg: "linear-gradient(135deg, rgba(139,92,246,0.15) 0%, rgba(139,92,246,0.02) 100%)" },
  "twitter.com":       { name: "Twitter / X",    accent: "#1d9bf0", bg: "linear-gradient(135deg, rgba(29,155,240,0.15) 0%, rgba(29,155,240,0.02) 100%)" },
  "x.com":             { name: "Twitter / X",    accent: "#1d9bf0", bg: "linear-gradient(135deg, rgba(29,155,240,0.15) 0%, rgba(29,155,240,0.02) 100%)" },
  "linkedin.com":      { name: "LinkedIn",        accent: "#0a66c2", bg: "linear-gradient(135deg, rgba(10,102,194,0.15) 0%, rgba(10,102,194,0.02) 100%)" },
  "spotify.com":       { name: "Spotify",         accent: "#1db954", bg: "linear-gradient(135deg, rgba(29,185,84,0.15) 0%, rgba(29,185,84,0.02) 100%)" },
  "instagram.com":     { name: "Instagram",       accent: "#e1306c", bg: "linear-gradient(135deg, rgba(225,48,108,0.15) 0%, rgba(225,48,108,0.02) 100%)" },
  "facebook.com":      { name: "Facebook",        accent: "#1877f2", bg: "linear-gradient(135deg, rgba(24,119,242,0.15) 0%, rgba(24,119,242,0.02) 100%)" },
  "reddit.com":        { name: "Reddit",          accent: "#ff4500", bg: "linear-gradient(135deg, rgba(255,69,0,0.15) 0%, rgba(255,69,0,0.02) 100%)" },
  "discord.com":       { name: "Discord",         accent: "#5865f2", bg: "linear-gradient(135deg, rgba(88,101,242,0.15) 0%, rgba(88,101,242,0.02) 100%)" },
  "youtube.com":       { name: "YouTube",         accent: "#ef4444", bg: "linear-gradient(135deg, rgba(239,68,68,0.15) 0%, rgba(239,68,68,0.02) 100%)" },
  "tiktok.com":        { name: "TikTok",          accent: "#06b6d4", bg: "linear-gradient(135deg, rgba(6,182,212,0.15) 0%, rgba(6,182,212,0.02) 100%)" },
  "telegram.org":      { name: "Telegram",        accent: "#26a5e4", bg: "linear-gradient(135deg, rgba(38,165,228,0.15) 0%, rgba(38,165,228,0.02) 100%)" },
  "t.me":              { name: "Telegram",        accent: "#26a5e4", bg: "linear-gradient(135deg, rgba(38,165,228,0.15) 0%, rgba(38,165,228,0.02) 100%)" },
  "twitch.tv":         { name: "Twitch",          accent: "#9146ff", bg: "linear-gradient(135deg, rgba(145,70,255,0.15) 0%, rgba(145,70,255,0.02) 100%)" },
  "pinterest.com":     { name: "Pinterest",       accent: "#e60023", bg: "linear-gradient(135deg, rgba(230,0,35,0.15) 0%, rgba(230,0,35,0.02) 100%)" },
  "medium.com":        { name: "Medium",          accent: "#10b981", bg: "linear-gradient(135deg, rgba(16,185,129,0.15) 0%, rgba(16,185,129,0.02) 100%)" },
  "hackerrank.com":    { name: "HackerRank",      accent: "#2ec4b6", bg: "linear-gradient(135deg, rgba(46,196,182,0.15) 0%, rgba(46,196,182,0.02) 100%)" },
  "stackoverflow.com": { name: "Stack Overflow",  accent: "#f48024", bg: "linear-gradient(135deg, rgba(244,128,36,0.15) 0%, rgba(244,128,36,0.02) 100%)" },
  "gitlab.com":        { name: "GitLab",          accent: "#fc6d26", bg: "linear-gradient(135deg, rgba(252,109,38,0.15) 0%, rgba(252,109,38,0.02) 100%)" },
  "gravatar.com":      { name: "Gravatar",        accent: "#1e8cbf", bg: "linear-gradient(135deg, rgba(30,140,191,0.15) 0%, rgba(30,140,191,0.02) 100%)" },
  "patreon.com":       { name: "Patreon",         accent: "#ff424d", bg: "linear-gradient(135deg, rgba(255,66,77,0.15) 0%, rgba(255,66,77,0.02) 100%)" },
  "paypal.com":        { name: "PayPal",          accent: "#003087", bg: "linear-gradient(135deg, rgba(0,48,135,0.15) 0%, rgba(0,48,135,0.02) 100%)" },
  "steam":             { name: "Steam",           accent: "#66c0f4", bg: "linear-gradient(135deg, rgba(102,192,244,0.15) 0%, rgba(102,192,244,0.02) 100%)" },
};

export const PLATFORM_SLUG_MAP: Record<string, string> = {
  youtube: "youtube.com",
  github: "github.com",
  twitter: "twitter.com",
  x: "x.com",
  linkedin: "linkedin.com",
  spotify: "spotify.com",
  instagram: "instagram.com",
  facebook: "facebook.com",
  reddit: "reddit.com",
  discord: "discord.com",
  tiktok: "tiktok.com",
  telegram: "telegram.org",
  twitch: "twitch.tv",
  pinterest: "pinterest.com",
  medium: "medium.com",
  coursera: "coursera.org",
  hackerrank: "hackerrank.com",
  stackoverflow: "stackoverflow.com",
  gitlab: "gitlab.com",
  gravatar: "gravatar.com",
  patreon: "patreon.com",
  paypal: "paypal.com",
  steam: "steam",
};

export function getBrand(domainOrSlug: string): PlatformBrand | null {
  if (!domainOrSlug) return null;
  const clean = domainOrSlug.toLowerCase().trim();
  const domain = PLATFORM_SLUG_MAP[clean] || clean;
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

export function getTypeBannerBg(accentColor: string): string {
  return `linear-gradient(135deg, ${accentColor}18 0%, ${accentColor}05 100%)`;
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
  size = 42,
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
      className="rounded-xl border-2 grid place-items-center shrink-0 overflow-hidden p-1.5 relative z-10 bg-surface shadow-sm"
      style={{
        width: size,
        height: size,
        borderColor: `${accentColor}88`,
        boxShadow: `0 2px 10px -2px ${accentColor}30`,
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

// ── Favicon & Brand Domain Helpers ──────────────────────────────────────────

export function getBrandDomain(
  profileUrl?: string,
  value?: string,
  platform?: string,
  platformDisplayName?: string
): string | undefined {
  if (profileUrl && profileUrl.includes(".") && !isIpAddress(profileUrl)) {
    const parsed = parseUrl(profileUrl);
    if (parsed.domain && !isIpAddress(parsed.domain)) return parsed.domain;
  }

  if (value && !isIpAddress(value)) {
    if (value.includes("@")) {
      const parts = value.split("@");
      if (parts.length > 1 && parts[1].includes(".") && !isIpAddress(parts[1])) return parts[1];
    } else if (
      value.includes(".") &&
      !value.startsWith("Yes") &&
      !value.startsWith("No")
    ) {
      const parsed = parseUrl(value);
      if (parsed.domain && !isIpAddress(parsed.domain)) return parsed.domain;
    }
  }

  const candidateSlugs = [platform, value].filter(Boolean) as string[];

  if (platformDisplayName) {
    const match = platformDisplayName.match(/\(([^)]+)\)/);
    if (match && match[1]) {
      candidateSlugs.push(match[1]);
    } else {
      candidateSlugs.push(platformDisplayName);
    }
  }

  for (const slug of candidateSlugs) {
    const cleanSlug = slug.toLowerCase().trim();
    const mappedDomain = PLATFORM_SLUG_MAP[cleanSlug];
    if (mappedDomain) return mappedDomain;
    if (PLATFORM_BRANDS[cleanSlug]) return cleanSlug;
    if (PLATFORM_BRANDS[`${cleanSlug}.com`]) return `${cleanSlug}.com`;
  }

  return undefined;
}

export function Favicon({ domain, size = 14 }: { domain: string; size?: number }) {
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
  url?: string;
  value?: string;
  type?: string;
  confidence?: number;
  platformDisplayName?: string;
  profileUrl?: string;
  platform?: string;
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
  platform,
  className,
  id,
}: ReconstructedProfileCardProps) {
  const targetUrl = profileUrl || (url && url.includes(".") && !isIpAddress(url) ? url : undefined);
  
  let href: string | undefined = undefined;
  let handle: string | null = null;

  if (targetUrl) {
    const parsed = parseUrl(targetUrl);
    href = parsed.href;
    handle = parsed.handle;
  }

  const domain = getBrandDomain(targetUrl, value, platform, platformDisplayName);

  const brand = domain ? getBrand(domain) : null;
  const accentColor = brand?.accent ?? getTypeAccent(type, platformDisplayName);
  const bannerBg = brand?.bg ?? getTypeBannerBg(accentColor);
  const displayName = platformDisplayName ?? brand?.name ?? (type ? type.toUpperCase() : (domain || "IDENTIFIER"));
  const displayValue = handle ? `@${handle}` : (value || domain || url || "");

  return (
    <div
      id={id}
      className={cn(
        "group relative rounded-xl border bg-surface overflow-hidden flex flex-col justify-between",
        "transition-all duration-300 hover:shadow-xl hover:-translate-y-0.5",
        className
      )}
      style={{
        borderColor: `${accentColor}35`,
        boxShadow: `0 4px 20px -4px ${accentColor}18, var(--shadow-elev)`,
      }}
    >
      {/* Top glowing accent stripe */}
      <div
        className="h-1 w-full shrink-0"
        style={{ background: `linear-gradient(90deg, ${accentColor}, ${accentColor}40)` }}
        aria-hidden="true"
      />

      {/* Header Banner */}
      <div
        className="px-3.5 pt-3 pb-2.5 flex items-center justify-between gap-2 shrink-0 border-b border-border/40"
        style={{ background: bannerBg }}
      >
        <div className="flex items-center gap-2.5 min-w-0">
          <PlatformLogoAvatar
            domain={domain}
            type={type}
            platformDisplayName={platformDisplayName}
            accentColor={accentColor}
            size={36}
          />
          <div className="min-w-0">
            <span
              className="text-[10px] font-mono font-bold uppercase tracking-widest block truncate"
              style={{ color: accentColor }}
            >
              {displayName}
            </span>
            {domain && (
              <span className="text-[10px] font-mono text-muted-foreground truncate block opacity-80">
                {domain}
              </span>
            )}
          </div>
        </div>

        <span
          className="text-[9px] font-mono font-bold uppercase tracking-widest px-2 py-0.5 rounded-sm border shrink-0"
          style={{
            color: accentColor,
            borderColor: `${accentColor}35`,
            background: `${accentColor}12`,
          }}
        >
          {type ?? "ENTITY"}
        </span>
      </div>

      {/* Card Content Body */}
      <div className="p-3.5 flex flex-col justify-between flex-1 gap-3">
        {/* Identifier Value Container — Clean, Crisp Surface (No Ugly Dark Grey Tint in Light Mode) */}
        <div className="p-3 rounded-lg border border-border/60 bg-surface-2/60 space-y-1 shadow-inner">
          <div className="text-[9px] font-mono font-semibold uppercase tracking-widest text-muted-foreground/70">
            Target Value
          </div>
          <div
            className="font-mono text-xs font-bold text-foreground break-all select-all leading-relaxed"
            title={displayValue}
          >
            {displayValue}
          </div>
        </div>

        {/* Intelligence Confidence Section */}
        {confidence !== undefined && (
          <div className="space-y-1">
            <div className="text-[9px] font-mono font-semibold uppercase tracking-widest text-muted-foreground/70 flex items-center justify-between">
              <span>Confidence Rating</span>
            </div>
            <ConfidenceBar
              value={confidence}
              ariaLabel={`Confidence rating for ${displayValue}`}
            />
          </div>
        )}

        {/* External Link Action Button */}
        {href ? (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={`Open ${displayName} profile for ${displayValue} in new tab`}
            className={cn(
              "group/link w-full inline-flex items-center justify-center gap-1.5 rounded-md border px-3 py-2",
              "text-xs font-mono font-bold uppercase tracking-wider transition-all duration-200",
              "hover:shadow-md hover:scale-[1.01] active:scale-[0.99]",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            )}
            style={{
              color: accentColor,
              borderColor: `${accentColor}40`,
              background: `${accentColor}12`,
            }}
          >
            <ExternalLink className="h-3.5 w-3.5 shrink-0 group-hover/link:translate-x-0.5 group-hover/link:-translate-y-0.5 transition-transform" aria-hidden="true" />
            <span>Open Native Profile</span>
          </a>
        ) : (
          <div className="w-full text-center py-1.5 text-[10px] font-mono uppercase tracking-widest text-muted-foreground/50 border border-dashed border-border/40 rounded-md">
            No Native URL
          </div>
        )}
      </div>
    </div>
  );
}

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
