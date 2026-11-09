import { Check } from "lucide-react";
import { showcaseChecklist } from "../content";
import { DashboardPreview } from "./dashboard-preview";
import { Reveal } from "./reveal";

export function ShowcaseSection() {
  return (
    <section className="px-4 pb-20 pt-6 sm:px-6">
      <div className="mx-auto grid max-w-6xl items-center gap-12 lg:grid-cols-[0.8fr_1.4fr]">
        <Reveal>
          <h2 className="text-3xl font-bold leading-tight tracking-tight text-emphasis sm:text-4xl">See Your Business From a Different Perspective.</h2>
          <p className="mt-4 text-base leading-relaxed text-muted">A unified view of your performance, products, customers, and more, all in one interactive dashboard.</p>
          <ul className="mt-6 space-y-3">
            {showcaseChecklist.map((item) => (
              <li key={item} className="flex items-center gap-3 text-sm text-foreground">
                <span className="grid size-5 shrink-0 place-items-center rounded bg-primary text-primary-foreground"><Check className="size-3.5" aria-hidden /></span>
                {item}
              </li>
            ))}
          </ul>
        </Reveal>
        <Reveal delay={0.1}>
          <DashboardPreview variant="full" />
        </Reveal>
      </div>
    </section>
  );
}
