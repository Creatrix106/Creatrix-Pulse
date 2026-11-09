import Link from "next/link";
import { buttonStyles } from "@/components/ui/button";
import { Logo } from "@/components/ui/logo";

export default function NotFound() {
  return (
    <main id="main" className="grid min-h-screen place-items-center bg-surface-muted px-6 text-center">
      <div>
        <Logo className="mb-8 justify-center" />
        <p className="text-sm font-semibold uppercase tracking-wider text-accent">404</p>
        <h1 className="mt-2 text-3xl font-semibold text-emphasis">We couldn’t find that page</h1>
        <p className="mx-auto mt-2 max-w-md text-muted">The link may be broken or the page may have been moved.</p>
        <div className="mt-6 flex justify-center gap-3">
          <Link href="/" className={buttonStyles()}>Go home</Link>
          <Link href="/dashboard" className={buttonStyles({ variant: "secondary" })}>Open dashboard</Link>
        </div>
      </div>
    </main>
  );
}
