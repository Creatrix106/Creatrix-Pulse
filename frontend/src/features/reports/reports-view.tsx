"use client";

import { useState } from "react";
import { Download, FileText } from "lucide-react";
import { ChartCard } from "@/components/charts";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { LoadingSkeleton, TableSkeleton } from "@/components/feedback/skeletons";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { FormField, Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { DatePresetSelector } from "@/components/filters/option-selectors";
import { METRIC_OPTIONS } from "@/config/filters";
import { featureFlags } from "@/config/features";
import { useDatasetId } from "@/hooks/use-dataset-id";
import { useDataset } from "@/hooks/use-datasets";
import { useFormatters } from "@/hooks/use-formatters";
import { useCreateReport, useReportHistory, useReportPreview } from "@/hooks/use-reports";
import { toast } from "@/stores/toast.store";
import type { MetricKey, DatePreset } from "@/types/filters";
import type { ReportConfig, ReportFormat, ReportRecord } from "@/types/report";
import { formatBytes, formatDateTime } from "@/utils/format";
import { slugify } from "@/utils/download";
import { apiClient } from "@/services/api-client";

function download(record: ReportRecord) {
  if (!record.downloadUrl) {
    toast.error("Download unavailable", "The server did not provide a download link for this report.");
    return;
  }
  const link = document.createElement("a");
  link.href = apiClient.resolveUrl(record.downloadUrl);
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.download = `${slugify(record.title)}.${record.format}`;
  document.body.appendChild(link);
  link.click();
  link.remove();
}

export function ReportsView() {
  const datasetId = useDatasetId();
  const f = useFormatters();
  const { data: dataset } = useDataset(datasetId);
  const [config, setConfig] = useState<ReportConfig>({ title: "Performance report", metrics: ["revenue", "orders", "units"], datePreset: "all", format: "csv" });

  const preview = useReportPreview(datasetId, config);
  const history = useReportHistory(datasetId);
  const create = useCreateReport(datasetId);

  const available = METRIC_OPTIONS.filter((m) => !m.requiresCost || dataset?.capabilities.cost);
  const toggleMetric = (key: MetricKey) =>
    setConfig((c) => ({ ...c, metrics: c.metrics.includes(key) ? c.metrics.filter((m) => m !== key) : [...c.metrics, key] }));

  const generate = () =>
    create.mutate(config, {
      onSuccess: (record) => {
        download(record);
        toast.success("Report generated", `${record.title} was added to your download history.`);
      },
    });

  return (
    <div className="space-y-6">
      <div className="grid gap-6 xl:grid-cols-3">
        <Card className="space-y-5 p-5 xl:col-span-1">
          <CardHeader title="Report settings" description="Choose what to include" />
          <FormField label="Report title" htmlFor="report-title">
            <Input id="report-title" value={config.title} onChange={(e) => setConfig({ ...config, title: e.target.value })} />
          </FormField>
          <FormField label="Date range" htmlFor="report-range">
            <DatePresetSelector value={config.datePreset} onChange={(datePreset: DatePreset) => setConfig({ ...config, datePreset })} label="Report date range" />
          </FormField>
          <fieldset>
            <legend className="mb-2 text-sm font-medium text-emphasis">Metrics</legend>
            <div className="grid gap-1 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
              {available.map((m) => (
                <label key={m.value} className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-surface-accent">
                  <input type="checkbox" className="size-4 accent-[var(--accent)]" checked={config.metrics.includes(m.value)} onChange={() => toggleMetric(m.value)} />
                  {m.label}
                </label>
              ))}
            </div>
            {dataset && !dataset.capabilities.cost && <p className="mt-2 text-xs text-muted">Cost and profit metrics are hidden because this dataset has no cost data.</p>}
          </fieldset>
          <FormField label="Export format" htmlFor="report-format">
            <Select id="report-format" value={config.format} onChange={(e) => setConfig({ ...config, format: e.target.value as ReportFormat })}>
              <option value="csv">CSV</option>
              <option value="json">JSON</option>
              <option value="pdf" disabled={!featureFlags.pdfExport}>PDF (unavailable)</option>
            </Select>
          </FormField>
          <Button className="w-full" onClick={generate} loading={create.isPending} disabled={config.metrics.length === 0 || !config.title.trim()}>
            <Download className="size-4" aria-hidden /> Generate &amp; download
          </Button>
        </Card>

        <div className="xl:col-span-2">
          <ChartCard title="Report preview" description={preview.data ? `${f.date(preview.data.period.from, "long")} – ${f.date(preview.data.period.to, "long")}` : "Monthly breakdown of the selected metrics"} className="h-full">
            {config.metrics.length === 0 ? (
              <EmptyState title="Select at least one metric" description="The preview updates as you change the settings." icon={FileText} />
            ) : preview.isPending ? (
              <div className="space-y-3"><LoadingSkeleton className="h-16 w-full" /><TableSkeleton rows={6} columns={Math.max(2, config.metrics.length + 1)} /></div>
            ) : preview.isError ? (
              <ErrorState message="The preview could not be generated." onRetry={() => preview.refetch()} />
            ) : (
              <div className="space-y-4">
                <h4 className="text-lg font-semibold text-emphasis">{preview.data.title}</h4>
                <dl className="grid gap-3 sm:grid-cols-3">
                  {preview.data.summary.map((s) => (
                    <div key={s.label} className="rounded-md bg-surface-accent p-3">
                      <dt className="text-xs text-muted">Total {s.label.toLowerCase()}</dt>
                      <dd className="tabular text-lg font-semibold text-emphasis">{f.kpi(s.value, s.format)}</dd>
                    </div>
                  ))}
                </dl>
                <div className="scrollbar-thin overflow-x-auto rounded-lg border border-border">
                  <table className="w-full min-w-max text-sm">
                    <thead className="bg-surface-muted text-xs uppercase tracking-wide text-muted">
                      <tr>{preview.data.columns.map((c) => <th key={c.key} scope="col" className={`px-4 py-2.5 font-semibold ${c.format === "date" ? "text-left" : "text-right"}`}>{c.label}</th>)}</tr>
                    </thead>
                    <tbody>
                      {preview.data.rows.map((row) => (
                        <tr key={String(row.date)} className="border-t border-border">
                          {preview.data.columns.map((c) => (
                            <td key={c.key} className={`tabular px-4 py-2 ${c.format === "date" ? "text-left" : "text-right"}`}>
                              {c.format === "date" ? f.period(String(row[c.key]), "month", "long") : f.kpi(Number(row[c.key]), c.format === "currency" ? "currency" : "number")}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </ChartCard>
        </div>
      </div>

      <ChartCard title="Download history" description="Previously generated reports for this dataset">
        {history.isPending ? (
          <TableSkeleton rows={3} columns={4} />
        ) : history.isError ? (
          <ErrorState message="Download history could not be loaded." onRetry={() => history.refetch()} />
        ) : history.data.length === 0 ? (
          <EmptyState title="No reports yet" description="Generated reports appear here so you can download them again." icon={FileText} />
        ) : (
          <div className="scrollbar-thin overflow-x-auto">
            <table className="w-full min-w-max text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-muted">
                <tr><th scope="col" className="py-2 pr-4 font-semibold">Report</th><th scope="col" className="py-2 pr-4 font-semibold">Generated</th><th scope="col" className="py-2 pr-4 font-semibold">Format</th><th scope="col" className="py-2 pr-4 font-semibold">Size</th><th scope="col" className="py-2"><span className="sr-only">Actions</span></th></tr>
              </thead>
              <tbody>
                {history.data.map((r) => (
                  <tr key={r.id} className="border-t border-border">
                    <td className="py-3 pr-4 font-medium text-foreground">{r.title}</td>
                    <td className="py-3 pr-4 text-muted">{formatDateTime(r.createdAt)}</td>
                    <td className="py-3 pr-4 uppercase text-muted">{r.format}</td>
                    <td className="py-3 pr-4 text-muted">{formatBytes(r.sizeBytes)}</td>
                    <td className="py-3 text-right"><Button size="sm" variant="secondary" onClick={() => download(r)}><Download className="size-4" aria-hidden /> Download</Button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </ChartCard>
    </div>
  );
}
