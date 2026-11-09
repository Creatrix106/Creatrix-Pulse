import Link from "next/link";
import type { ReactNode } from "react";
import { BarChart3, ShieldCheck, Sparkles, Upload } from "lucide-react";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { Logo } from "@/components/ui/logo";

const points = [
  { icon: Upload, text: "Upload CSV or Excel files in seconds" },
  { icon: BarChart3, text: "Interactive dashboards built from your data" },
  { icon: Sparkles, text: "Evidence-backed insights and reports" },
  { icon: ShieldCheck, text: "You stay in control of your datasets" },
];

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-[1fr_1.05fr]">
      <aside className="relative hidden flex-col justify-between overflow-hidden bg-sidebar p-12 text-white lg:flex">
        <div aria-hidden className="pointer-events-none absolute -bottom-32 -right-32 size-96 rounded-full bg-white/5 blur-2xl" />
        <Link href="/" aria-label="Creatrix Pulse home"><Logo tone="inverse" /></Link>
        <div className="relative">
          <h2 className="text-4xl font-bold leading-tight tracking-tight">Turn your data into your next move.</h2>
          <ul className="mt-8 space-y-4">
            {points.map((p) => (
              <li key={p.text} className="flex items-center gap-3 text-white/85">
                <span className="grid size-9 place-items-center rounded-md bg-white/10"><p.icon className="size-[18px]" aria-hidden /></span>
                {p.text}
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-sm text-white/60">© {new Date().getFullYear()} Creatrix Pulse</p>
      </aside>
      <div className="flex flex-col bg-background">
        <div className="flex items-center justify-between p-4 sm:p-6 lg:justify-end">
          <Link href="/" aria-label="Creatrix Pulse home" className="lg:hidden"><Logo /></Link>
          <ThemeToggle />
        </div>
        <main id="main" className="flex flex-1 items-center justify-center px-4 pb-12 sm:px-6">
          <div className="w-full max-w-md">{children}</div>
        </main>
      </div>
    </div>
  );
}
