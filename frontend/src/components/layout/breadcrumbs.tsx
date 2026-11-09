import Link from "next/link";
import { ChevronRight } from "lucide-react";

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

export function Breadcrumbs({ items }: { items: BreadcrumbItem[] }) {
  return (
    <nav aria-label="Breadcrumb">
      <ol className="flex min-w-0 items-center gap-1.5 text-sm">
        {items.map((item, i) => {
          const last = i === items.length - 1;
          return (
            <li key={`${item.label}-${i}`} className="flex min-w-0 items-center gap-1.5">
              {item.href && !last ? (
                <Link href={item.href} className="truncate text-muted hover:text-foreground">{item.label}</Link>
              ) : (
                <span className="truncate font-medium text-emphasis" aria-current={last ? "page" : undefined}>{item.label}</span>
              )}
              {!last && <ChevronRight className="size-3.5 shrink-0 text-muted" aria-hidden />}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
