import Link from "next/link";
import { Logo } from "@/components/ui/logo";
import { footerColumns } from "../content";

export function MarketingFooter() {
  return (
    <footer className="border-t border-border bg-background px-4 py-12 sm:px-6">
      <div className="mx-auto grid max-w-6xl gap-10 md:grid-cols-[1.4fr_repeat(3,1fr)]">
        <div>
          <Logo />
          <p className="mt-3 max-w-xs text-sm leading-relaxed text-muted">A business intelligence platform that turns your data into clear insights, interactive dashboards, and smarter decisions.</p>
        </div>
        {footerColumns.map((col) => (
          <nav key={col.title} aria-label={col.title}>
            <h3 className="text-sm font-semibold text-emphasis">{col.title}</h3>
            <ul className="mt-3 space-y-2">
              {col.links.map((l) => (
                <li key={l.label}><Link href={l.href} className="text-sm text-muted hover:text-foreground">{l.label}</Link></li>
              ))}
            </ul>
          </nav>
        ))}
      </div>
      <p className="mx-auto mt-10 max-w-6xl border-t border-border pt-6 text-sm text-muted">© {new Date().getFullYear()} Creatrix Pulse. All rights reserved.</p>
    </footer>
  );
}
