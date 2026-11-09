import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Reveal } from "./reveal";

export function FinalCta() {
  return (
    <section className="relative overflow-hidden bg-sidebar px-4 py-16 text-center text-white sm:px-6">
      <div aria-hidden className="pointer-events-none absolute -left-24 bottom-[-120px] h-72 w-[520px] rounded-full bg-white/5 blur-2xl" />
      <Reveal className="relative mx-auto max-w-2xl">
        <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">Your Data Is Ready. Are You?</h2>
        <p className="mt-3 text-base text-white/80">Start exploring your business data and discover the insights hidden within it.</p>
        <Link href="/register" className="mt-8 inline-flex h-12 items-center gap-2 rounded-md bg-white px-6 text-base font-semibold text-[#102a56] shadow-card transition-opacity hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white">
          Get Started with Creatrix Pulse <ArrowRight className="size-4" aria-hidden />
        </Link>
        <p className="mt-4 text-sm text-white/70">Upload your first dataset and begin exploring.</p>
      </Reveal>
    </section>
  );
}
