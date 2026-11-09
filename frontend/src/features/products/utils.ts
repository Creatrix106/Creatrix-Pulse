import type { ProductPerformance } from "@/types/analytics";

/** Top N products plus an "Other products" slice so the donut always sums to the full total. */
export function contributionSlices(products: ProductPerformance[], top = 5): { name: string; value: number; share: number }[] {
  const sorted = [...products].sort((a, b) => b.revenue - a.revenue);
  const head = sorted.slice(0, top).map((p) => ({ name: p.name, value: p.revenue, share: p.share }));
  const rest = sorted.slice(top);
  if (rest.length === 0) return head;
  return [...head, { name: "Other products", value: rest.reduce((s, p) => s + p.revenue, 0), share: rest.reduce((s, p) => s + p.share, 0) }];
}
