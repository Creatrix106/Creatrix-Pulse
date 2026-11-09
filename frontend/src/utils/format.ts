import type { GroupBy } from "@/types/filters";
import type { KpiFormat } from "@/types/analytics";

export interface FormatSettings {
  currency: string;
  locale: string;
}

export interface Formatters {
  currency: (value: number, opts?: { compact?: boolean }) => string;
  number: (value: number) => string;
  compact: (value: number) => string;
  /** Takes a value already expressed as a percentage (12.3 -> "12.3%"). */
  percent: (value: number, opts?: { signed?: boolean; digits?: number }) => string;
  date: (iso: string, style?: "short" | "long") => string;
  period: (iso: string, groupBy: GroupBy, style?: "short" | "long") => string;
  kpi: (value: number, format: KpiFormat, opts?: { compact?: boolean }) => string;
}

const UTC = "UTC";

export function parseIsoDate(iso: string): Date {
  return new Date(`${iso.slice(0, 10)}T00:00:00Z`);
}

export function createFormatters({ currency, locale }: FormatSettings): Formatters {
  const currencyFull = new Intl.NumberFormat(locale, { style: "currency", currency, maximumFractionDigits: 0 });
  const currencyCompact = new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    notation: "compact",
    maximumFractionDigits: 1,
  });
  const numberFull = new Intl.NumberFormat(locale, { maximumFractionDigits: 1 });
  const numberCompact = new Intl.NumberFormat(locale, { notation: "compact", maximumFractionDigits: 1 });

  const date: Formatters["date"] = (iso, style = "short") =>
    new Intl.DateTimeFormat(locale, {
      day: "numeric",
      month: "short",
      year: style === "long" ? "numeric" : undefined,
      timeZone: UTC,
    }).format(parseIsoDate(iso));

  const period: Formatters["period"] = (iso, groupBy, style = "short") => {
    const d = parseIsoDate(iso);
    if (groupBy === "month") {
      return new Intl.DateTimeFormat(locale, {
        month: "short",
        year: style === "long" ? "numeric" : undefined,
        timeZone: UTC,
      }).format(d);
    }
    const label = new Intl.DateTimeFormat(locale, { day: "numeric", month: "short", timeZone: UTC }).format(d);
    return groupBy === "week" && style === "long" ? `Week of ${label}` : label;
  };

  const percent: Formatters["percent"] = (value, opts) => {
    const digits = opts?.digits ?? 1;
    const sign = opts?.signed && value > 0 ? "+" : "";
    return `${sign}${value.toFixed(digits)}%`;
  };

  const compactCurrency = (v: number) => currencyCompact.format(v);

  return {
    currency: (value, opts) => (opts?.compact ? compactCurrency(value) : currencyFull.format(value)),
    number: (value) => numberFull.format(value),
    compact: (value) => numberCompact.format(value),
    percent,
    date,
    period,
    kpi: (value, format, opts) => {
      if (format === "currency") return opts?.compact ? compactCurrency(value) : currencyFull.format(value);
      if (format === "percent") return percent(value);
      return numberFull.format(value);
    },
  };
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let value = bytes / 1024;
  let i = 0;
  while (value >= 1024 && i < units.length - 1) {
    value /= 1024;
    i++;
  }
  return `${value.toFixed(value < 10 ? 1 : 0)} ${units[i]}`;
}

export function formatDateTime(iso: string, locale = "en-IN"): string {
  return new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(new Date(iso));
}
