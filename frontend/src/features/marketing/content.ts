import { BarChart3, Boxes, Database, FileText, Monitor, Sparkles, Target, TrendingUp, Upload, Users, type LucideIcon } from "lucide-react";

export interface IconCopy {
  icon: LucideIcon;
  title: string;
  description: string;
}

export const valuePropositions: IconCopy[] = [
  { icon: BarChart3, title: "Understand Performance", description: "Monitor revenue, orders, products, and important business metrics." },
  { icon: TrendingUp, title: "Discover Patterns", description: "Identify trends, compare performance, and uncover unusual changes." },
  { icon: Target, title: "Make Informed Decisions", description: "Use meaningful insights and reports to understand where your business stands." },
];

export const features: IconCopy[] = [
  { icon: Monitor, title: "Interactive Dashboards", description: "Visualize important business metrics. Monitor performance through charts and KPI cards. Explore data through interactive filters." },
  { icon: Boxes, title: "Product Analytics", description: "Identify top-selling products. Compare product performance. Understand category contributions." },
  { icon: Users, title: "Customer Analytics", description: "Understand customer purchasing patterns. Explore new and returning customers. Examine customer performance where suitable data is available." },
  { icon: Database, title: "Revenue & Cost Analysis", description: "Monitor revenue and expenses. Understand profit and margins when cost data is available. Compare financial performance over time." },
  { icon: Sparkles, title: "Smart Insights", description: "Identify important trends. Highlight unusual changes. Generate understandable, evidence-based summaries." },
  { icon: FileText, title: "Reports & Exports", description: "Generate useful business reports. Export analyzed data. Share performance summaries." },
];

export const steps: IconCopy[] = [
  { icon: Upload, title: "Upload Your Data", description: "Import your business datasets through a simple CSV or Excel upload." },
  { icon: BarChart3, title: "Analyze Performance", description: "Creatrix Pulse processes your records and transforms them into meaningful metrics and visualizations." },
  { icon: Sparkles, title: "Discover Insights", description: "Explore trends, compare performance, and understand what deserves your attention." },
];

export const showcaseChecklist = [
  "Key performance metrics at a glance",
  "Revenue and trend analysis",
  "Product, category, and regional breakdowns",
  "Actionable insights to guide your next move",
];

export const footerColumns: { title: string; links: { label: string; href: string }[] }[] = [
  {
    title: "Navigation",
    links: [
      { label: "Home", href: "/" },
      { label: "Features", href: "/#features" },
      { label: "How It Works", href: "/#how-it-works" },
      { label: "About", href: "/#about" },
    ],
  },
  {
    title: "Features",
    links: [
      { label: "Dashboards", href: "/#features" },
      { label: "Product Analytics", href: "/#features" },
      { label: "Customer Analytics", href: "/#features" },
      { label: "Revenue & Cost Analysis", href: "/#features" },
    ],
  },
  {
    title: "Get started",
    links: [
      { label: "Create an account", href: "/register" },
      { label: "Log in", href: "/login" },
      { label: "Upload a dataset", href: "/upload" },
    ],
  },
];
