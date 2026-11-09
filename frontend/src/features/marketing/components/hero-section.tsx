import Link from "next/link";
import { ArrowRight, BarChart3, Sparkles, Upload } from "lucide-react";
import { buttonStyles } from "@/components/ui/button";
import { siteConfig } from "@/config/site";
import { DashboardPreview } from "./dashboard-preview";
import { Reveal } from "./reveal";

export function HeroSection() {
  return (
    <section className="relative overflow-hidden">
      <div aria-hidden className="pointer-events-none absolute -right-40 top-0 h-[520px] w-[820px] rounded-full bg-surface-accent opacity-80 blur-3xl" />
      <div className="relative mx-auto grid max-w-6xl items-center gap-12 px-4 py-14 sm:px-6 lg:grid-cols-[1fr_1.1fr] lg:py-20">
        <Reveal>
          <span className="inline-block rounded bg-surface-accent px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wider text-emphasis">Business Intelligence, Simplified</span>
          <h1 className="mt-5 text-4xl font-extrabold leading-[1.05] tracking-tight text-emphasis sm:text-5xl lg:text-[3.4rem]">Turn Your Data Into <span className="whitespace-nowrap">Your Next Move.</span></h1>
          <p className="mt-5 max-w-md text-lg leading-relaxed text-muted">{siteConfig.description}</p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/register" className={buttonStyles({ size: "lg" })}>Get Started <ArrowRight className="size-4" aria-hidden /></Link>
            <Link href="/#features" className={buttonStyles({ size: "lg", variant: "secondary" })}>Explore Features</Link>
          </div>
          <ul className="mt-10 flex flex-wrap items-center gap-y-3 text-sm font-medium text-emphasis">
            {[
              { icon: Upload, label: "Upload." },
              { icon: BarChart3, label: "Analyze." },
              { icon: Sparkles, label: "Discover." },
            ].map((item, i) => (
              <li key={item.label} className={`flex items-center gap-2 pr-5 ${i > 0 ? "border-l border-border-strong pl-5" : ""}`}>
                <item.icon className="size-5 text-accent" aria-hidden /> {item.label}
              </li>
            ))}
          </ul>
        </Reveal>
        <Reveal delay={0.1}>
          <DashboardPreview variant="compact" />
        </Reveal>
      </div>
    </section>
  );
}
