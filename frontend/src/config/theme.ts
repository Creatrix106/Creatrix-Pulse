import { Monitor, Moon, Sun, type LucideIcon } from "lucide-react";

export type ThemePreference = "light" | "dark" | "system";

export const THEME_STORAGE_KEY = "cp-theme";

export const themeOptions: { value: ThemePreference; label: string; icon: LucideIcon }[] = [
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
  { value: "system", label: "System", icon: Monitor },
];
