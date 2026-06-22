export type WidgetTone = "neutral" | "accent" | "warning";

export interface DashboardWidget {
  id: string;
  title: string;
  description: string;
  tone: WidgetTone;
  region: "left-rail" | "hero" | "primary" | "secondary";
}

export interface DashboardTransportStatus {
  sse: "idle" | "connecting" | "connected" | "error";
  websocket: "idle" | "connecting" | "connected" | "error";
}

export interface DashboardEvent {
  id: string;
  source: "sse" | "websocket" | "system";
  message: string;
  createdAt: string;
}

export interface ClaimSummary {
  id: number;
  claimNumber: string;
  status: string;
  claimType: string;
  customerId: number;
}
