export interface CurrencyOption {
  code: string;
  label: string;
  locale: string;
}

/** Add a currency here and it appears in Settings automatically. */
export const CURRENCY_OPTIONS: CurrencyOption[] = [
  { code: "INR", label: "Indian Rupee (₹)", locale: "en-IN" },
  { code: "USD", label: "US Dollar ($)", locale: "en-US" },
  { code: "EUR", label: "Euro (€)", locale: "de-DE" },
  { code: "GBP", label: "British Pound (£)", locale: "en-GB" },
];

export const DEFAULT_CURRENCY = CURRENCY_OPTIONS[0];
