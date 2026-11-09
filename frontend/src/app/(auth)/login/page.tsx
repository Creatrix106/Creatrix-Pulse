import type { Metadata } from "next";
import { LoginForm } from "@/features/auth/components/login-form";

export const metadata: Metadata = { title: "Log in" };

export default function LoginPage() {
  return (
    <>
      <h1 className="text-3xl font-bold tracking-tight text-emphasis">Welcome back</h1>
      <p className="mb-8 mt-2 text-muted">Log in to continue exploring your business data.</p>
      <LoginForm />
    </>
  );
}
