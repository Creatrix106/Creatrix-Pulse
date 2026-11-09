"use client";

import { Moon, Sun } from "lucide-react";
import { useThemeStore } from "@/stores/theme.store";

/** Light/dark switch. Icons are swapped with CSS so there is no hydration mismatch. */
export function ThemeToggle() {
  const setTheme = useThemeStore((s) => s.setTheme);
  return (
    <button
      type="button"
      onClick={() => setTheme(document.documentElement.classList.contains("dark") ? "light" : "dark")}
      className="grid size-9 place-items-center rounded-md text-muted transition-colors hover:bg-surface-accent hover:text-foreground"
      aria-label="Toggle color theme"
    >
      <Sun className="size-[18px] dark:hidden" aria-hidden />
      <Moon className="hidden size-[18px] dark:block" aria-hidden />
    </button>
  );
}
