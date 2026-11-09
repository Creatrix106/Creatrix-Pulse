"use client";

import Link from "next/link";
import { Upload } from "lucide-react";
import { Logo } from "@/components/ui/logo";
import { useDataset } from "@/hooks/use-datasets";
import { NavList } from "./nav-list";

export function Sidebar({ datasetId }: { datasetId: string }) {
  const { data: dataset } = useDataset(datasetId);
  return (
    <aside className="fixed inset-y-0 left-0 z-40 hidden w-[var(--sidebar-width)] flex-col border-r border-sidebar-border bg-sidebar lg:flex">
      <div className="flex h-[var(--topbar-height)] shrink-0 items-center border-b border-sidebar-border px-5">
        <Link href="/" aria-label="Creatrix Pulse home">
          <Logo tone="inverse" />
        </Link>
      </div>
      <div className="scrollbar-thin flex-1 overflow-y-auto px-3 py-5">
        <NavList datasetId={datasetId} />
      </div>
      <div className="space-y-3 border-t border-sidebar-border p-4">
        <div className="rounded-md bg-white/5 p-3">
          <p className="text-xs text-sidebar-muted">Active dataset</p>
          <p className="mt-0.5 truncate text-sm font-medium text-white">{dataset?.name ?? "Loading…"}</p>
        </div>
        <Link href="/upload" className="flex items-center justify-center gap-2 rounded-md bg-white px-3 py-2 text-sm font-semibold text-[#102a56] transition-opacity hover:opacity-90">
          <Upload className="size-4" aria-hidden /> Upload dataset
        </Link>
      </div>
    </aside>
  );
}
