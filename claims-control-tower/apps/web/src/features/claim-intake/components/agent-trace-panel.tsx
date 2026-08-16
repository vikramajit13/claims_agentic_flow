import { useQuery } from "@tanstack/react-query";

import { getClaimTrace } from "@/lib/http";
import type { WorkflowTraceEvent } from "@/types/api";

import { formatTimestamp } from "../lib/helpers";
import { PanelShell } from "./panel-shell";

type AgentTracePanelProps = {
  claimId: number | null;
};

export function AgentTracePanel({ claimId }: AgentTracePanelProps) {
  const traceQuery = useQuery({
    queryKey: ["claim-trace", claimId],
    queryFn: () => getClaimTrace(claimId as number),
    enabled: claimId !== null,
    refetchInterval: 10000
  });

  const trace = traceQuery.data;
  const events = trace?.events ?? [];

  return (
    <PanelShell
      eyebrow="Agent trace"
      title="Graph decisions and tool timeline"
      status={claimId ? `${events.length} events` : "Idle"}
      description="Shows graph choice, judge verdicts, tool execution, and human review milestones."
      testId="agent-trace-panel"
    >
      {!claimId ? (
        <div className="rounded-[18px] border border-dashed border-slate-900/12 bg-white/70 px-4 py-5 text-sm text-slate-500">
          Create a claim and start a workflow to populate the trace.
        </div>
      ) : null}
      {claimId && events.length === 0 ? (
        <div className="rounded-[18px] border border-dashed border-slate-900/12 bg-white/70 px-4 py-5 text-sm text-slate-500">
          No trace events yet for this claim.
        </div>
      ) : null}
      <ol className="grid gap-3">
        {events.map((event) => (
          <li key={event.id} className="rounded-[20px] border border-slate-900/10 bg-white/85 px-4 py-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.16em] text-teal-800">{event.stage}</p>
                <h3 className="text-base font-semibold text-slate-900">{event.title}</h3>
              </div>
              <span className="rounded-full border border-slate-900/10 bg-white px-3 py-1 text-xs uppercase tracking-[0.12em] text-slate-600">
                {event.status}
              </span>
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-700">{event.detail}</p>
            <TraceMetadata event={event} />
            {event.timestamp ? <div className="mt-3 text-xs text-slate-500">{formatTimestamp(event.timestamp)}</div> : null}
          </li>
        ))}
      </ol>
    </PanelShell>
  );
}

function TraceMetadata({ event }: { event: WorkflowTraceEvent }) {
  const entries = Object.entries(event.metadata ?? {}).filter(([, value]) => value !== null && value !== undefined && value !== "");
  if (entries.length === 0) {
    return null;
  }

  return (
    <div className="mt-3 grid gap-2 rounded-[16px] bg-slate-950/[0.03] p-3">
      {entries.map(([key, value]) => (
        <div key={key} className="grid gap-1">
          <div className="text-[11px] font-bold uppercase tracking-[0.14em] text-slate-500">{formatLabel(key)}</div>
          <TraceValue value={value} />
        </div>
      ))}
    </div>
  );
}

function TraceValue({ value }: { value: unknown }) {
  if (typeof value === "boolean") {
    return <div className="text-sm text-slate-700">{value ? "true" : "false"}</div>;
  }
  if (typeof value === "number" || typeof value === "string") {
    return <div className="text-sm text-slate-700">{String(value)}</div>;
  }
  if (Array.isArray(value)) {
    if (value.length === 0) {
      return <div className="text-sm text-slate-500">None</div>;
    }
    return (
      <div className="flex flex-wrap gap-2">
        {value.map((item, index) => (
          <span
            key={`${index}-${JSON.stringify(item)}`}
            className="rounded-full border border-slate-900/10 bg-white px-3 py-1 text-xs text-slate-700"
          >
            {formatInlineValue(item)}
          </span>
        ))}
      </div>
    );
  }
  if (isPlainObject(value)) {
    return (
      <pre className="overflow-x-auto rounded-[12px] bg-white/80 p-3 text-xs leading-5 text-slate-700">
        {JSON.stringify(value, null, 2)}
      </pre>
    );
  }
  return <div className="text-sm text-slate-700">{String(value)}</div>;
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function formatInlineValue(value: unknown) {
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
}

function formatLabel(label: string) {
  return label.replaceAll("_", " ");
}
