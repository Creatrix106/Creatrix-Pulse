import { valuePropositions } from "../content";
import { Reveal } from "./reveal";

export function ValueSection() {
  return (
    <section id="about" className="scroll-mt-20 px-4 py-16 sm:px-6">
      <div className="mx-auto max-w-5xl text-center">
        <Reveal>
          <h2 className="text-3xl font-bold tracking-tight text-emphasis sm:text-4xl">Your Business Data Has More to Say.</h2>
          <p className="mx-auto mt-4 max-w-3xl text-base leading-relaxed text-muted">
            Business data contains valuable information, but extracting meaningful insights from spreadsheets can be time-consuming. Creatrix Pulse makes that process simpler by turning your data into an understandable and interactive analytics experience.
          </p>
        </Reveal>
        <ul className="mt-12 grid gap-8 text-left md:grid-cols-3 md:divide-x md:divide-border">
          {valuePropositions.map((v, i) => (
            <li key={v.title} className="md:px-8 md:first:pl-0 md:last:pr-0">
              <Reveal delay={i * 0.08} className="flex items-start gap-4">
                <span className="grid size-14 shrink-0 place-items-center rounded-xl bg-surface-accent text-accent"><v.icon className="size-7" aria-hidden /></span>
                <div>
                  <h3 className="font-semibold text-emphasis">{v.title}</h3>
                  <p className="mt-1 text-sm leading-relaxed text-muted">{v.description}</p>
                </div>
              </Reveal>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
