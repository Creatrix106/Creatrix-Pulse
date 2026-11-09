"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { InlineError } from "@/components/feedback/inline-error";
import { Button } from "@/components/ui/button";
import { FormField, Input } from "@/components/ui/input";
import { useRegister } from "@/hooks/use-auth";
import { getErrorMessage } from "@/services/api-client";
import { registerSchema, type RegisterValues } from "../schemas";
import { PasswordInput } from "./password-input";

export function RegisterForm() {
  const router = useRouter();
  const signUp = useRegister();
  const { register, handleSubmit, formState: { errors } } = useForm<RegisterValues>({ resolver: zodResolver(registerSchema) });

  return (
    <form
      noValidate
      className="space-y-5"
      onSubmit={handleSubmit(({ name, email, password }) => signUp.mutate({ name, email, password }, { onSuccess: () => router.push("/dashboard") }))}
    >
      {signUp.isError && <InlineError message={getErrorMessage(signUp.error)} />}
      <FormField label="Full name" htmlFor="name" error={errors.name?.message}>
        <Input id="name" autoComplete="name" placeholder="Asha Verma" aria-invalid={!!errors.name} {...register("name")} />
      </FormField>
      <FormField label="Work email" htmlFor="email" error={errors.email?.message}>
        <Input id="email" type="email" autoComplete="email" placeholder="you@company.com" aria-invalid={!!errors.email} {...register("email")} />
      </FormField>
      <FormField label="Password" htmlFor="password" error={errors.password?.message} hint="At least 8 characters, including a number.">
        <PasswordInput id="password" autoComplete="new-password" aria-invalid={!!errors.password} {...register("password")} />
      </FormField>
      <FormField label="Confirm password" htmlFor="confirmPassword" error={errors.confirmPassword?.message}>
        <PasswordInput id="confirmPassword" autoComplete="new-password" aria-invalid={!!errors.confirmPassword} {...register("confirmPassword")} />
      </FormField>
      <Button type="submit" size="lg" className="w-full" loading={signUp.isPending}>Create account</Button>
      <p className="text-center text-sm text-muted">
        Already have an account? <Link href="/login" className="font-semibold text-accent hover:underline">Log in</Link>
      </p>
    </form>
  );
}
