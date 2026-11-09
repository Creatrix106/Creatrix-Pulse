import { ArrowRight } from "lucide-react";
import { steps } from "../content";
import { Reveal } from "./reveal";

export function HowItWorksSection() {
  return (
    <section id="how-it-works" className="scroll-mt-16 px-4 py-16 sm:px-6">
      <div className="mx-auto max-w-5xl">
        <Reveal>
          <h2 className="text-center text-3xl font-bold tracking-tight text-emphasis sm:text-4xl">From Raw Data to Clear Insights.</h2>
        </Reveal>
        <ol className="mt-12 grid items-start gap-10 md:grid-cols-[1fr_auto_1fr_auto_1fr]">
          {steps.flatMap((step, i) => {
            const item = (
              <li key={step.title} className="flex items-start gap-4">
                <Reveal delay={i * 0.1} className="flex items-start gap-4">
                  <span className="grid size-9 shrink-0 place-items-center rounded-full bg-primary text-sm font-bold text-primary-foreground">{String(i + 1).padStart(2, "0")}</span>
                  <div>
                    <step.icon className="mb-2 size-6 text-accent" aria-hidden />
                    <h3 className="font-semibold text-emphasis">{step.title}</h3>
                    <p className="mt-1 text-sm leading-relaxed text-muted">{step.description}</p>
                  </div>
                </Reveal>
              </li>
            );
            return i < steps.length - 1
              ? [item, <li key={`arrow-${i}`} aria-hidden className="mt-3 hidden text-muted md:block"><ArrowRight className="size-5" /></li>]
              : [item];
          })}
        </ol>
      </div>
    </section>
  );
}
