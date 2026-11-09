"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { InlineError } from "@/components/feedback/inline-error";
import { Button } from "@/components/ui/button";
import { FormField, Input } from "@/components/ui/input";
import { useLogin } from "@/hooks/use-auth";
import { getErrorMessage } from "@/services/api-client";
import { loginSchema, type LoginValues } from "../schemas";
import { PasswordInput } from "./password-input";

export function LoginForm() {
  const router = useRouter();
  const login = useLogin();
  const { register, handleSubmit, formState: { errors } } = useForm<LoginValues>({ resolver: zodResolver(loginSchema) });

  return (
    <form noValidate className="space-y-5" onSubmit={handleSubmit((values) => login.mutate(values, { onSuccess: () => router.push("/dashboard") }))}>
      {login.isError && <InlineError message={getErrorMessage(login.error)} />}
      <FormField label="Email" htmlFor="email" error={errors.email?.message}>
        <Input id="email" type="email" autoComplete="email" placeholder="you@company.com" aria-invalid={!!errors.email} aria-describedby={errors.email ? "email-error" : undefined} {...register("email")} />
      </FormField>
      <FormField label="Password" htmlFor="password" error={errors.password?.message}>
        <PasswordInput id="password" autoComplete="current-password" placeholder="At least 8 characters" aria-invalid={!!errors.password} aria-describedby={errors.password ? "password-error" : undefined} {...register("password")} />
      </FormField>
      <Button type="submit" size="lg" className="w-full" loading={login.isPending}>Log in</Button>
      <p className="text-center text-sm text-muted">
        New to Creatrix Pulse? <Link href="/register" className="font-semibold text-accent hover:underline">Create an account</Link>
      </p>
    </form>
  );
}
