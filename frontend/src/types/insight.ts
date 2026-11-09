export type InsightType = "positive" | "negative" | "anomaly" | "observation" | "recommendation";

export interface InsightEvidence {
  label: string;
  value: string;
}

/** Insights are produced by the backend; the frontend only renders them. */
export interface Insight {
  id: string;
  type: InsightType;
  title: string;
  summary: string;
  /** Metric the insight relates to, e.g. "revenue". */
  metric?: string;
  evidence: InsightEvidence[];
}
