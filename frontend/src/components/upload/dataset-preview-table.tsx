import { Badge } from "@/components/ui/badge";
import type { DatasetProfile } from "@/types/dataset";

export function DatasetPreviewTable({ profile }: { profile: DatasetProfile }) {
  return (
    <div className="scrollbar-thin overflow-x-auto rounded-lg border border-border">
      <table className="w-full min-w-max text-sm">
        <caption className="sr-only">Preview of the first {profile.previewRows.length} rows</caption>
        <thead className="bg-surface-muted">
          <tr>
            {profile.columns.map((c) => (
              <th key={c.name} scope="col" className="whitespace-nowrap px-4 py-3 text-left align-bottom font-semibold text-emphasis">
                {c.name}
                <Badge variant="neutral" className="ml-2 align-middle font-normal">{c.type}</Badge>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {profile.previewRows.map((row, r) => (
            <tr key={r} className="border-t border-border">
              {row.map((cell, c) => (
                <td key={c} className="max-w-56 truncate whitespace-nowrap px-4 py-2 text-foreground">{cell || <span className="text-muted">—</span>}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
