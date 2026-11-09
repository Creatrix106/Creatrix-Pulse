"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { LogIn, LogOut, Settings } from "lucide-react";
import { Popover } from "@/components/ui/popover";
import { getDashboardHref } from "@/config/navigation";
import { useLogout } from "@/hooks/use-auth";
import { useAuthStore } from "@/stores/auth.store";

const itemStyles = "flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-foreground hover:bg-surface-accent";

export function UserMenu({ datasetId }: { datasetId?: string }) {
  const user = useAuthStore((s) => s.user);
  const router = useRouter();
  const logout = useLogout();
  const initials = user ? user.name.split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase() : "G";

  return (
    <Popover
      align="end"
      panelClassName="w-60"
      trigger={({ open, toggle, panelId }) => (
        <button
          type="button"
          onClick={toggle}
          aria-expanded={open}
          aria-controls={panelId}
          aria-label="Open user menu"
          className="grid size-9 place-items-center rounded-full bg-primary text-xs font-semibold text-primary-foreground transition-opacity hover:opacity-90"
        >
          {initials}
        </button>
      )}
    >
      {(close) => (
        <div>
          <div className="border-b border-border px-3 pb-2 pt-1">
            <p className="truncate text-sm font-semibold text-emphasis">{user?.name ?? "Guest"}</p>
            <p className="truncate text-xs text-muted">{user?.email ?? "Not signed in"}</p>
          </div>
          <div className="pt-1">
            {datasetId && <Link href={getDashboardHref(datasetId, "settings")} onClick={close} className={itemStyles}>
              <Settings className="size-4" aria-hidden /> Settings
            </Link>}
            {user ? (
              <button
                type="button"
                className={itemStyles}
                onClick={() => {
                  close();
                  logout.mutate(undefined, { onSuccess: () => router.push("/login") });
                }}
              >
                <LogOut className="size-4" aria-hidden /> Sign out
              </button>
            ) : (
              <Link href="/login" onClick={close} className={itemStyles}>
                <LogIn className="size-4" aria-hidden /> Log in
              </Link>
            )}
          </div>
        </div>
      )}
    </Popover>
  );
}
