"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { LogOut } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button, buttonStyles } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { FormField, Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { DATE_PRESETS } from "@/config/filters";
import { featureFlags } from "@/config/features";
import { CURRENCY_OPTIONS } from "@/config/locale";
import { tableConfig } from "@/config/table";
import { themeOptions } from "@/config/theme";
import { useLogout } from "@/hooks/use-auth";
import { useAuthStore } from "@/stores/auth.store";
import { usePreferencesStore } from "@/stores/preferences.store";
import { useThemeStore } from "@/stores/theme.store";
import { toast } from "@/stores/toast.store";
import type { DatePreset } from "@/types/filters";
import { cn } from "@/utils/cn";

const profileSchema = z.object({
  name: z.string().trim().min(2, "Enter your full name."),
  email: z.email("Enter a valid email address."),
});
type ProfileValues = z.infer<typeof profileSchema>;

function ProfileSettings() {
  const user = useAuthStore((s) => s.user);
  const setUser = useAuthStore((s) => s.setUser);
  const form = useForm<ProfileValues>({
    resolver: zodResolver(profileSchema),
    values: { name: user?.name ?? "", email: user?.email ?? "" },
  });

  return (
    <Card className="p-5">
      <CardHeader title="Profile" description="How you appear in Creatrix Pulse" />
      {user ? (
        <form
          className="mt-5 grid max-w-xl gap-4"
          noValidate
          onSubmit={form.handleSubmit((values) => {
            setUser({ ...user, ...values });
            toast.success("Profile updated");
          })}
        >
          <FormField label="Full name" htmlFor="profile-name" error={form.formState.errors.name?.message}>
            <Input id="profile-name" autoComplete="name" aria-invalid={!!form.formState.errors.name} {...form.register("name")} />
          </FormField>
          <FormField label="Email" htmlFor="profile-email" error={form.formState.errors.email?.message}>
            <Input id="profile-email" type="email" autoComplete="email" aria-invalid={!!form.formState.errors.email} {...form.register("email")} />
          </FormField>
          <div className="flex items-center gap-3">
            <Button type="submit" disabled={!form.formState.isDirty}>Save changes</Button>
            <span className="text-xs text-muted">{featureFlags.avatarUpload ? "" : "Profile photo upload is not available yet."}</span>
          </div>
        </form>
      ) : (
        <p className="mt-4 text-sm text-muted">
          You’re browsing as a guest. <Link href="/login" className="font-medium text-accent hover:underline">Log in</Link> to edit your profile.
        </p>
      )}
    </Card>
  );
}

function AppearanceSettings() {
  const theme = useThemeStore((s) => s.theme);
  const setTheme = useThemeStore((s) => s.setTheme);
  const currency = usePreferencesStore((s) => s.currency);
  const update = usePreferencesStore((s) => s.update);

  return (
    <Card className="p-5">
      <CardHeader title="Appearance" description="Theme and number formatting" />
      <div className="mt-5 space-y-5">
        <fieldset>
          <legend className="mb-2 text-sm font-medium text-emphasis">Theme</legend>
          <div className="grid max-w-md grid-cols-3 gap-2" role="radiogroup">
            {themeOptions.map((o) => (
              <button
                key={o.value}
                type="button"
                role="radio"
                aria-checked={theme === o.value}
                onClick={() => setTheme(o.value)}
                className={cn("flex flex-col items-center gap-1.5 rounded-md border px-3 py-3 text-sm font-medium transition-colors", theme === o.value ? "border-accent bg-surface-accent text-emphasis" : "border-border hover:bg-surface-accent")}
              >
                <o.icon className="size-5" aria-hidden /> {o.label}
              </button>
            ))}
          </div>
        </fieldset>
        <FormField label="Currency" htmlFor="pref-currency" hint="Applies to every monetary value in the dashboard." className="max-w-md">
          <Select
            id="pref-currency"
            value={currency}
            onChange={(e) => {
              const option = CURRENCY_OPTIONS.find((c) => c.code === e.target.value);
              if (option) update({ currency: option.code, locale: option.locale });
            }}
          >
            {CURRENCY_OPTIONS.map((c) => (
              <option key={c.code} value={c.code}>{c.label}</option>
            ))}
          </Select>
        </FormField>
      </div>
    </Card>
  );
}

function DashboardPreferences() {
  const prefs = usePreferencesStore();
  const rows: { id: string; label: string; description: string; checked: boolean; onChange: (v: boolean) => void }[] = [
    { id: "pref-insights", label: "Show insights on the overview", description: "Display the Key insights card on the overview page.", checked: prefs.showInsightsOnOverview, onChange: (v) => prefs.update({ showInsightsOnOverview: v }) },
    { id: "pref-compact", label: "Compact chart axis numbers", description: "Use 1.2K / 3.4M style labels on chart axes.", checked: prefs.compactNumbers, onChange: (v) => prefs.update({ compactNumbers: v }) },
  ];
  return (
    <Card className="p-5">
      <CardHeader title="Dashboard preferences" description="Defaults used whenever you open a dashboard" />
      <div className="mt-5 grid max-w-xl gap-4">
        <FormField label="Default date range" htmlFor="pref-range">
          <Select id="pref-range" value={prefs.defaultDatePreset} onChange={(e) => prefs.update({ defaultDatePreset: e.target.value as DatePreset })}>
            {DATE_PRESETS.filter((p) => p.value !== "custom").map((p) => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </Select>
        </FormField>
        <FormField label="Rows per page in Data Explorer" htmlFor="pref-rows">
          <Select id="pref-rows" value={prefs.pageSize} onChange={(e) => prefs.update({ pageSize: Number(e.target.value) })}>
            {tableConfig.pageSizeOptions.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </Select>
        </FormField>
        {rows.map((r) => (
          <div key={r.id} className="flex items-start justify-between gap-4">
            <label htmlFor={r.id} className="cursor-pointer">
              <span className="block text-sm font-medium text-emphasis">{r.label}</span>
              <span className="block text-sm text-muted">{r.description}</span>
            </label>
            <Switch id={r.id} label={r.label} checked={r.checked} onChange={r.onChange} />
          </div>
        ))}
        <div><Button variant="ghost" size="sm" onClick={() => { prefs.reset(); toast.info("Preferences reset to defaults"); }}>Reset to defaults</Button></div>
      </div>
    </Card>
  );
}

function AccountSettings() {
  const user = useAuthStore((s) => s.user);
  const router = useRouter();
  const logout = useLogout();
  const [busy, setBusy] = useState(false);

  return (
    <Card className="p-5">
      <CardHeader title="Account" description="Sign-in and security" />
      <dl className="mt-5 grid max-w-xl gap-3 text-sm">
        <div className="flex justify-between gap-4"><dt className="text-muted">Email</dt><dd className="font-medium">{user?.email ?? "Not signed in"}</dd></div>
        <div className="flex justify-between gap-4"><dt className="text-muted">Role</dt><dd>{user ? <Badge variant="accent">{user.role}</Badge> : "—"}</dd></div>
      </dl>
      <div className="mt-5 flex flex-wrap items-center gap-2">
        {user ? (
          <Button variant="secondary" loading={busy} onClick={() => { setBusy(true); logout.mutate(undefined, { onSettled: () => router.push("/login") }); }}>
            <LogOut className="size-4" aria-hidden /> Sign out
          </Button>
        ) : (
          <Link href="/login" className={buttonStyles({ variant: "secondary" })}>Log in</Link>
        )}
        <Button variant="secondary" disabled={!featureFlags.changePassword} title="Available once the backend supports password changes">Change password</Button>
        <Button variant="ghost" disabled={!featureFlags.deleteAccount} className="text-danger" title="Available once the backend supports account deletion">Delete account</Button>
      </div>
      {(!featureFlags.changePassword || !featureFlags.deleteAccount) && <p className="mt-3 text-xs text-muted">Password changes and account deletion are unavailable until they are supported by the backend.</p>}
    </Card>
  );
}

export function SettingsView() {
  return (
    <div className="grid gap-6 xl:grid-cols-2">
      <ProfileSettings />
      <AppearanceSettings />
      <DashboardPreferences />
      <AccountSettings />
    </div>
  );
}
