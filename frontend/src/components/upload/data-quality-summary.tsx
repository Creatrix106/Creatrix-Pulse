import { Badge } from "@/components/ui/badge";
import type { DatasetProfile } from "@/types/dataset";

export function DataQualitySummary({ profile }: { profile: DatasetProfile }) {
  const stats = [
    { label: "Rows", value: profile.rowCount.toLocaleString() },
    { label: "Columns", value: String(profile.columns.length) },
    { label: "Missing cells", value: `${profile.missingPercent.toFixed(1)}%` },
    { label: "Duplicate rows", value: profile.duplicateRows.toLocaleString() },
  ];
  return (
    <div className="space-y-4">
      <dl className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {stats.map((s) => (
          <div key={s.label} className="rounded-md bg-surface-accent p-3">
            <dt className="text-xs text-muted">{s.label}</dt>
            <dd className="tabular text-xl font-semibold text-emphasis">{s.value}</dd>
          </div>
        ))}
      </dl>
      <details className="group rounded-lg border border-border">
        <summary className="cursor-pointer select-none px-4 py-3 text-sm font-medium text-emphasis">Column information</summary>
        <div className="scrollbar-thin overflow-x-auto border-t border-border">
          <table className="w-full min-w-max text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-muted">
              <tr>
                <th scope="col" className="px-4 py-2 font-semibold">Column</th>
                <th scope="col" className="px-4 py-2 font-semibold">Type</th>
                <th scope="col" className="px-4 py-2 text-right font-semibold">Missing</th>
                <th scope="col" className="px-4 py-2 text-right font-semibold">Unique</th>
                <th scope="col" className="px-4 py-2 font-semibold">Sample values</th>
              </tr>
            </thead>
            <tbody>
              {profile.columns.map((c) => (
                <tr key={c.name} className="border-t border-border">
                  <td className="px-4 py-2 font-medium">{c.name}</td>
                  <td className="px-4 py-2"><Badge>{c.type}</Badge></td>
                  <td className="tabular px-4 py-2 text-right">{c.missing.toLocaleString()}</td>
                  <td className="tabular px-4 py-2 text-right">{c.unique.toLocaleString()}</td>
                  <td className="max-w-64 truncate px-4 py-2 text-muted">{c.sample.join(", ") || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}
