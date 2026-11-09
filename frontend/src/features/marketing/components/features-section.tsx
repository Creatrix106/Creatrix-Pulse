import { features } from "../content";
import { Reveal } from "./reveal";

export function FeaturesSection() {
  return (
    <section id="features" className="scroll-mt-16 bg-surface-accent/60 px-4 py-16 sm:px-6">
      <div className="mx-auto max-w-6xl">
        <Reveal>
          <h2 className="text-center text-3xl font-bold tracking-tight text-emphasis sm:text-4xl">Everything You Need to Understand Your Business.</h2>
        </Reveal>
        <ul className="mt-12 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {features.map((feature, i) => (
            <li key={feature.title}>
              <Reveal delay={(i % 3) * 0.07} className="h-full">
                <article className="flex h-full gap-4 rounded-lg border border-border bg-surface p-5 shadow-card transition-shadow hover:shadow-popover">
                  <span className="grid size-12 shrink-0 place-items-center rounded-lg bg-surface-accent text-accent"><feature.icon className="size-6" aria-hidden /></span>
                  <div>
                    <h3 className="font-semibold text-emphasis">{feature.title}</h3>
                    <p className="mt-1.5 text-sm leading-relaxed text-muted">{feature.description}</p>
                  </div>
                </article>
              </Reveal>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
