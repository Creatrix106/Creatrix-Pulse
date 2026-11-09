import type { CanonicalField } from "@/types/dataset";

export const SUPPORTED_FILE_FORMATS = [
  { extension: ".csv", label: "CSV", mime: ["text/csv", "application/vnd.ms-excel"], kind: "csv" },
  {
    extension: ".xlsx",
    label: "Excel",
    mime: ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
    kind: "excel",
  },
  { extension: ".xls", label: "Excel (legacy)", mime: ["application/vnd.ms-excel"], kind: "excel" },
] as const;

export const FILE_ACCEPT = SUPPORTED_FILE_FORMATS.map((f) => f.extension).join(",");
export const MAX_FILE_SIZE_MB = 25;
export const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;
export const PREVIEW_ROW_COUNT = 8;

export interface CanonicalFieldConfig {
  id: CanonicalField;
  label: string;
  description: string;
  required: boolean;
  /** Header names (normalised) used to auto-suggest a mapping. */
  aliases: string[];
}

/** Fields the analytics engine understands. Optional fields unlock extra analytics. */
export const CANONICAL_FIELDS: CanonicalFieldConfig[] = [
  { id: "date", label: "Order date", description: "When the sale happened", required: true, aliases: ["date", "order date", "orderdate", "invoice date", "transaction date", "day", "created at"] },
  { id: "product", label: "Product", description: "Product or item name", required: true, aliases: ["product", "product name", "item", "item name", "sku", "title"] },
  { id: "revenue", label: "Revenue", description: "Sales amount per row", required: true, aliases: ["revenue", "sales", "amount", "total", "total sales", "net sales", "order value", "line total"] },
  { id: "quantity", label: "Quantity", description: "Units sold (enables units & AOV)", required: false, aliases: ["quantity", "qty", "units", "units sold"] },
  { id: "orderId", label: "Order ID", description: "Unique order reference", required: false, aliases: ["order id", "orderid", "order no", "invoice", "invoice no", "transaction id"] },
  { id: "category", label: "Category", description: "Product category (enables category analytics)", required: false, aliases: ["category", "product category", "department", "type"] },
  { id: "region", label: "Region", description: "Geography (enables regional analytics)", required: false, aliases: ["region", "state", "zone", "area", "city", "location"] },
  { id: "customer", label: "Customer", description: "Customer id (enables customer analytics)", required: false, aliases: ["customer", "customer id", "customerid", "client", "buyer", "customer name"] },
  { id: "cost", label: "Cost", description: "Cost of goods (enables profit & margin)", required: false, aliases: ["cost", "cogs", "total cost", "expense", "unit cost"] },
];
