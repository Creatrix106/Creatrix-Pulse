import Link from "next/link";
import type { ReactNode } from "react";
import { Logo } from "@/components/ui/logo";
import { cn } from "@/utils/cn";
import { ThemeToggle } from "./theme-toggle";
import { UserMenu } from "./user-menu";

interface AppLayoutProps {
  children: ReactNode;
  /** Max width of the content column. */
  width?: "md" | "lg" | "xl";
}

const widths = { md: "max-w-2xl", lg: "max-w-4xl", xl: "max-w-6xl" };

/** Lightweight application frame for flows outside the dashboard (upload, processing). */
export function AppLayout({ children, width = "lg" }: AppLayoutProps) {
  return (
    <div className="min-h-screen bg-surface-muted">
      <header className="border-b border-border bg-background">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <Link href="/" aria-label="Creatrix Pulse home">
            <Logo />
          </Link>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <UserMenu />
          </div>
        </div>
      </header>
      <main id="main" className={cn("mx-auto px-4 py-8 sm:px-6 sm:py-12", widths[width])}>
        {children}
      </main>
    </div>
  );
}
