"use client";

import { useState } from "react";
import Link from "next/link";
import { Menu, X } from "lucide-react";
import { buttonStyles } from "@/components/ui/button";
import { Logo } from "@/components/ui/logo";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { marketingNav } from "@/config/site";

export function MarketingNav() {
  const [open, setOpen] = useState(false);
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <Link href="/" aria-label="Creatrix Pulse home"><Logo /></Link>

        <nav aria-label="Primary" className="hidden items-center gap-8 md:flex">
          {marketingNav.map((item) => (
            <Link key={item.label} href={item.href} className="text-sm font-medium text-foreground transition-colors hover:text-accent">{item.label}</Link>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Link href="/login" className={buttonStyles({ variant: "secondary", className: "hidden sm:inline-flex" })}>Log In</Link>
          <Link href="/register" className={buttonStyles({ className: "hidden sm:inline-flex" })}>Get Started</Link>
          <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open} aria-controls="mobile-menu" aria-label={open ? "Close menu" : "Open menu"} className="grid size-9 place-items-center rounded-md hover:bg-surface-accent md:hidden">
            {open ? <X className="size-5" aria-hidden /> : <Menu className="size-5" aria-hidden />}
          </button>
        </div>
      </div>

      {open && (
        <div id="mobile-menu" className="border-t border-border bg-background px-4 pb-4 pt-2 md:hidden">
          <nav aria-label="Mobile" className="flex flex-col">
            {marketingNav.map((item) => (
              <Link key={item.label} href={item.href} onClick={() => setOpen(false)} className="rounded-md px-3 py-2.5 text-sm font-medium hover:bg-surface-accent">{item.label}</Link>
            ))}
          </nav>
          <div className="mt-3 grid grid-cols-2 gap-2">
            <Link href="/login" className={buttonStyles({ variant: "secondary" })}>Log In</Link>
            <Link href="/register" className={buttonStyles()}>Get Started</Link>
          </div>
        </div>
      )}
    </header>
  );
}
