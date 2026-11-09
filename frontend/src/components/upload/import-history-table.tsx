import { DatasetStatusBadge } from "@/features/datasets/components/dataset-status-badge";
import type { Dataset } from "@/types/dataset";
import { formatBytes, formatDateTime } from "@/utils/format";

/** Upload history: one row per imported file. */
export function ImportHistoryTable({ datasets }: { datasets: Dataset[] }) {
  const sorted = [...datasets].sort((a, b) => b.uploadedAt.localeCompare(a.uploadedAt));
  return (
    <div className="scrollbar-thin overflow-x-auto">
      <table className="w-full min-w-max text-sm">
        <caption className="sr-only">Upload history</caption>
        <thead className="text-left text-xs uppercase tracking-wide text-muted">
          <tr>
            <th scope="col" className="py-2 pr-4 font-semibold">File</th>
            <th scope="col" className="py-2 pr-4 font-semibold">Uploaded</th>
            <th scope="col" className="py-2 pr-4 text-right font-semibold">Rows</th>
            <th scope="col" className="py-2 pr-4 text-right font-semibold">Size</th>
            <th scope="col" className="py-2 font-semibold">Status</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((d) => (
            <tr key={d.id} className="border-t border-border">
              <td className="py-3 pr-4 font-medium text-foreground">{d.fileName}</td>
              <td className="py-3 pr-4 text-muted">{formatDateTime(d.uploadedAt)}</td>
              <td className="tabular py-3 pr-4 text-right">{d.rowCount.toLocaleString()}</td>
              <td className="tabular py-3 pr-4 text-right text-muted">{formatBytes(d.fileSize)}</td>
              <td className="py-3"><DatasetStatusBadge status={d.status} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
