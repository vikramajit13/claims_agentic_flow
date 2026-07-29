import type { ClaimResponse, WorkflowRunResponse } from "@/types/api";

import { formatTimestamp } from "../lib/helpers";
import { PanelShell } from "./panel-shell";
import { StatusPill } from "./status-pill";

type WorkflowPanelProps = {
  activeClaim: ClaimResponse | null;
  latestWorkflow: WorkflowRunResponse | null;
  isStarting: boolean;
  onStartWorkflow: () => Promise<unknown>;
  onResetSession: () => void;
};

export function WorkflowPanel({
  activeClaim,
  latestWorkflow,
  isStarting,
  onStartWorkflow,
  onResetSession
}: WorkflowPanelProps) {
  return (
    <PanelShell
      eyebrow="Step 3"
      title="Start backend workflow"
      status={isStarting ? "Starting" : "Ready"}
      description="This calls your existing workflow API so you can verify the handoff from claim intake into graph orchestration."
      testId="workflow-panel"
    >
      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          className="rounded-2xl bg-gradient-to-br from-teal-700 to-emerald-500 px-5 py-3 font-bold text-white transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-60"
          onClick={() => void onStartWorkflow()}
          disabled={!activeClaim || isStarting}
          data-testid="start-workflow-button"
        >
          {isStarting ? "Starting workflow..." : "Start workflow"}
        </button>
        <button
          type="button"
          className="rounded-2xl border border-slate-900/10 bg-white/70 px-5 py-3 font-semibold text-slate-800 transition hover:bg-white"
          onClick={onResetSession}
        >
          Reset session
        </button>
      </div>

      {latestWorkflow ? (
        <div className="mt-5 rounded-[22px] border border-slate-900/8 bg-white/92 p-5">
          <div className="flex flex-col items-start justify-between gap-3 sm:flex-row sm:items-center">
            <h3 className="text-base font-semibold text-slate-900">Workflow {latestWorkflow.id}</h3>
            <StatusPill value={latestWorkflow.status} />
          </div>
          <dl className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
            <div className="rounded-2xl bg-slate-50/90 px-4 py-3">
              <dt className="mb-1 text-xs uppercase tracking-[0.08em] text-slate-500">Step</dt>
              <dd>{latestWorkflow.current_step}</dd>
            </div>
            <div className="rounded-2xl bg-slate-50/90 px-4 py-3">
              <dt className="mb-1 text-xs uppercase tracking-[0.08em] text-slate-500">HITL</dt>
              <dd>{latestWorkflow.hitl_required ? "Required" : "Not required"}</dd>
            </div>
            <div className="rounded-2xl bg-slate-50/90 px-4 py-3 md:col-span-2">
              <dt className="mb-1 text-xs uppercase tracking-[0.08em] text-slate-500">Next action</dt>
              <dd>{latestWorkflow.next_action}</dd>
            </div>
            <div className="rounded-2xl bg-slate-50/90 px-4 py-3">
              <dt className="mb-1 text-xs uppercase tracking-[0.08em] text-slate-500">Updated</dt>
              <dd>{formatTimestamp(latestWorkflow.updated_at)}</dd>
            </div>
          </dl>
        </div>
      ) : null}
    </PanelShell>
  );
}
