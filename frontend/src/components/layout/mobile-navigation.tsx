"use client";

import { useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { AnimatePresence, motion } from "motion/react";
import { Upload, X } from "lucide-react";
import { Logo } from "@/components/ui/logo";
import { useUiStore } from "@/stores/ui.store";
import { NavList } from "./nav-list";

export function MobileNavigation({ datasetId }: { datasetId: string }) {
  const open = useUiStore((s) => s.mobileNavOpen);
  const setOpen = useUiStore((s) => s.setMobileNavOpen);
  const pathname = usePathname();

  useEffect(() => {
    setOpen(false);
  }, [pathname, setOpen]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, setOpen]);

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <motion.div className="absolute inset-0 bg-overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setOpen(false)} aria-hidden />
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label="Navigation menu"
            className="absolute inset-y-0 left-0 flex w-72 max-w-[85%] flex-col bg-sidebar shadow-modal"
            initial={{ x: "-100%" }}
            animate={{ x: 0 }}
            exit={{ x: "-100%" }}
            transition={{ duration: 0.2, ease: [0.2, 0, 0, 1] }}
          >
            <div className="flex h-[var(--topbar-height)] items-center justify-between border-b border-sidebar-border px-5">
              <Logo tone="inverse" />
              <button type="button" onClick={() => setOpen(false)} aria-label="Close navigation" className="rounded-md p-1.5 text-sidebar-fg hover:bg-white/10">
                <X className="size-5" aria-hidden />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-3 py-5">
              <NavList datasetId={datasetId} onNavigate={() => setOpen(false)} />
            </div>
            <div className="border-t border-sidebar-border p-4">
              <Link href="/upload" className="flex items-center justify-center gap-2 rounded-md bg-white px-3 py-2 text-sm font-semibold text-[#102a56]">
                <Upload className="size-4" aria-hidden /> Upload dataset
              </Link>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
