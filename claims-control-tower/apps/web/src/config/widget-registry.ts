import type { DashboardWidget } from "@/types";

export const widgetRegistry: DashboardWidget[] = [
  {
    id: "portfolio-overview",
    title: "Portfolio Overview",
    description: "Global snapshot for queue health, submission mix, and claims awaiting graph execution.",
    tone: "accent",
    region: "hero"
  },
  {
    id: "live-activity",
    title: "Live Activity",
    description: "SSE and WebSocket event stream surface for claim updates, customer guidance, and future agent nudges.",
    tone: "neutral",
    region: "primary"
  },
  {
    id: "customer-guidance",
    title: "Customer Guidance",
    description: "Reserved space for future prompt-driven view targeting and contextual UI handoffs.",
    tone: "neutral",
    region: "primary"
  },
  {
    id: "human-review",
    title: "Human Review",
    description: "HITL and exception handling queue for graph interrupts and operator review.",
    tone: "warning",
    region: "secondary"
  },
  {
    id: "document-intake",
    title: "Document Intake",
    description: "Pre-signed upload, OCR intake status, and S3-backed evidence pipeline visibility.",
    tone: "neutral",
    region: "left-rail"
  }
];
