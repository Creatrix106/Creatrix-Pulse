import Link from "next/link";
import { Upload } from "lucide-react";
import type { ReactNode } from "react";
import { EmptyState } from "@/components/feedback/empty-state";
import { buttonStyles } from "@/components/ui/button";
import type { Capability } from "@/types/api";

interface CapabilityGateProps<T> {
  result: Capability<T>;
  title: string;
  children: (data: T) => ReactNode;
}

/**
 * Renders analytics only when the backend says the dataset supports them.
 * When data is missing the reason from the API is shown – no numbers are invented.
 */
export function CapabilityGate<T>({ result, title, children }: CapabilityGateProps<T>) {
  if (result.available) return <>{children(result.data)}</>;
  return (
    <EmptyState
      title={title}
      description={result.reason}
      action={
        <Link href="/upload" className={buttonStyles({ variant: "secondary" })}>
          <Upload className="size-4" aria-hidden /> Upload a dataset with this data
        </Link>
      }
    />
  );
}
