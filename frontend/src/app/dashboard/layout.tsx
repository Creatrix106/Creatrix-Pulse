import type { ReactNode } from "react";
import { AuthGuard } from "@/components/auth/auth-guard";

export default function DashboardAuthLayout({ children }: { children: ReactNode }) {
  return <AuthGuard>{children}</AuthGuard>;
}
