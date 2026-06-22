import clsx from "clsx";

import { useDashboardStore } from "@/store/dashboard-store";
import { useViewStore } from "@/store/view-store";
import type { DashboardWidget } from "@/types";

import "./dashboard-shell.css";

interface DashboardShellProps {
  widgets: DashboardWidget[];
  focusedWidgetId: string | null;
}

export function DashboardShell({ widgets, focusedWidgetId }: DashboardShellProps) {
  const claims = useDashboardStore((state) => state.claims);
  const events = useDashboardStore((state) => state.events);
  const transportStatus = useDashboardStore((state) => state.transportStatus);
  const focusWidget = useViewStore((state) => state.focusWidget);

  return (
    <div className="dashboard-shell">
      <aside className="dashboard-rail">
        <span className="eyebrow">Claims Control Tower</span>
        <h1>Dashboard starter for graph-native claims operations.</h1>
        <p>
          This shell is designed for live claim operations, HITL checkpoints, and future prompt-driven UI targeting
          without jumping straight into a fully agentic UI runtime.
        </p>
        <div className="transport-grid">
          <TransportCard label="SSE" state={transportStatus.sse} />
          <TransportCard label="WebSocket" state={transportStatus.websocket} />
        </div>
      </aside>

      <section className="dashboard-canvas">
        <div className="canvas-header">
          <div>
            <span className="eyebrow">Widget Map</span>
            <h2>Addressable dashboard regions</h2>
          </div>
          <div className="claim-badge">{claims.length} tracked claims</div>
        </div>

        <div className="widget-grid">
          {widgets.map((widget) => (
            <article
              key={widget.id}
              className={clsx("widget-card", `region-${widget.region}`, `tone-${widget.tone}`, {
                focused: widget.id === focusedWidgetId
              })}
              onClick={() => focusWidget(widget.id)}
            >
              <div className="widget-card-header">
                <span className="widget-id">{widget.id}</span>
                <span className="widget-region">{widget.region}</span>
              </div>
              <h3>{widget.title}</h3>
              <p>{widget.description}</p>
              {widget.id === "portfolio-overview" ? (
                <ul className="metric-list">
                  <li>Draft + submitted claim visibility</li>
                  <li>Graph bootstrap readiness</li>
                  <li>OCR and document intake signal</li>
                </ul>
              ) : null}
              {widget.id === "live-activity" ? (
                <div className="event-feed">
                  {events.length === 0 ? (
                    <span className="empty-state">No live events yet. Add SSE or WebSocket endpoints later.</span>
                  ) : (
                    events.slice(0, 5).map((event) => (
                      <div key={event.id} className="event-row">
                        <strong>{event.source}</strong>
                        <span>{event.message}</span>
                      </div>
                    ))
                  )}
                </div>
              ) : null}
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

function TransportCard({ label, state }: { label: string; state: string }) {
  return (
    <div className={clsx("transport-card", `state-${state}`)}>
      <span>{label}</span>
      <strong>{state}</strong>
    </div>
  );
}
