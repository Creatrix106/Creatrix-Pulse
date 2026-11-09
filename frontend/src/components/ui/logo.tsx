import { cn } from "@/utils/cn";
import { siteConfig } from "@/config/site";

export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={cn("size-6", className)} aria-hidden>
      <rect x="2" y="12" width="5" height="10" rx="1" fill="currentColor" opacity="0.55" />
      <rect x="9.5" y="7" width="5" height="15" rx="1" fill="currentColor" opacity="0.8" />
      <rect x="17" y="2" width="5" height="20" rx="1" fill="currentColor" />
    </svg>
  );
}

interface LogoProps {
  className?: string;
  /** Tone of the wordmark: "default" follows the theme, "inverse" is for navy backgrounds. */
  tone?: "default" | "inverse";
  showName?: boolean;
}

export function Logo({ className, tone = "default", showName = true }: LogoProps) {
  return (
    <span className={cn("inline-flex items-center gap-2", tone === "inverse" ? "text-white" : "text-emphasis", className)}>
      <LogoMark className={tone === "inverse" ? "text-white" : "text-accent"} />
      {showName && <span className="text-lg font-bold tracking-tight">{siteConfig.name}</span>}
    </span>
  );
}
