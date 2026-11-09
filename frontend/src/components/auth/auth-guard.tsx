"use client";

import { useEffect, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { ErrorState } from "@/components/feedback/error-state";
import { PageSkeleton } from "@/components/feedback/skeletons";
import { useCurrentUser } from "@/hooks/use-auth";
import { getErrorMessage, isApiError } from "@/services/api-client";

export function AuthGuard({ children }: { children: ReactNode }) {
  const router = useRouter();
  const session = useCurrentUser();
  const unauthorized = isApiError(session.error) && session.error.status === 401;
  const shouldRedirect = unauthorized || (!session.isPending && !session.isError && !session.data);

  useEffect(() => {
    const redirect = () => router.replace("/login");
    window.addEventListener("creatrix:unauthorized", redirect);
    if (shouldRedirect) redirect();
    return () => window.removeEventListener("creatrix:unauthorized", redirect);
  }, [router, shouldRedirect]);

  if (session.isPending || unauthorized) return <PageSkeleton />;
  if (session.isError) {
    return <ErrorState title="We couldn’t verify your session" message={getErrorMessage(session.error)} onRetry={() => session.refetch()} />;
  }
  if (!session.data) return <PageSkeleton />;
  return <>{children}</>;
}
