import type { Metadata } from "next";
import { RegisterForm } from "@/features/auth/components/register-form";

export const metadata: Metadata = { title: "Create account" };

export default function RegisterPage() {
  return (
    <>
      <h1 className="text-3xl font-bold tracking-tight text-emphasis">Create your account</h1>
      <p className="mb-8 mt-2 text-muted">Start turning raw datasets into clear, actionable insights.</p>
      <RegisterForm />
    </>
  );
}
