"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { canAccessPage, dashboardGroups, dashboardPages, getDashboardHref } from "@/config/navigation";
import { useAuthStore } from "@/stores/auth.store";
import { cn } from "@/utils/cn";

interface NavListProps {
  datasetId: string;
  onNavigate?: () => void;
}

/** Config-driven navigation shared by the sidebar and mobile drawer. */
export function NavList({ datasetId, onNavigate }: NavListProps) {
  const pathname = usePathname();
  const role = useAuthStore((s) => s.user?.role);

  return (
    <nav aria-label="Dashboard" className="space-y-6">
      {dashboardGroups.map((group) => {
        const pages = dashboardPages.filter((p) => p.group === group.id && canAccessPage(p, role));
        if (pages.length === 0) return null;
        return (
          <div key={group.id}>
            <p className="mb-2 px-3 text-xs font-semibold uppercase tracking-wider text-sidebar-muted">{group.label}</p>
            <ul className="space-y-0.5">
              {pages.map((page) => {
                const href = getDashboardHref(datasetId, page.segment);
                const active = page.segment === "" ? pathname === href : pathname === href || pathname.startsWith(`${href}/`);
                return (
                  <li key={page.id}>
                    <Link
                      href={href}
                      onClick={onNavigate}
                      aria-current={active ? "page" : undefined}
                      className={cn(
                        "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                        active ? "bg-sidebar-active text-white" : "text-sidebar-fg hover:bg-white/5 hover:text-white",
                      )}
                    >
                      <page.icon className="size-[18px] shrink-0" aria-hidden />
                      {page.label}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        );
      })}
    </nav>
  );
}
