import Link from "next/link";
import { EmptyState } from "@/components/feedback/empty-state";
import { buttonStyles } from "@/components/ui/button";
import { FileQuestion } from "lucide-react";

export default function DashboardNotFound() {
  return <EmptyState icon={FileQuestion} title="Page not found" description="This dashboard section does not exist." action={<Link href="/dashboard" className={buttonStyles()}>Back to dashboard</Link>} />;
}
