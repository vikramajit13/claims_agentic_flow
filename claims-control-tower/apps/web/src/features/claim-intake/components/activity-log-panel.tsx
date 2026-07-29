import { formatTimestamp } from "../lib/helpers";
import { PanelShell } from "./panel-shell";

type ActivityEntry = {
  id: string;
  message: string;
  createdAt: string;
};

type ActivityLogPanelProps = {
  entries: ActivityEntry[];
};

export function ActivityLogPanel({ entries }: ActivityLogPanelProps) {
  return (
    <PanelShell eyebrow="Run log" title="What the UI is doing" status={`${entries.length} events`} testId="activity-log-panel">
      <ol className="grid gap-3">
        {entries.length === 0 ? <li className="text-sm text-slate-500">No activity yet. Create a claim to start.</li> : null}
        {entries.map((entry) => (
          <li
            key={entry.id}
            className="flex flex-col justify-between gap-2 rounded-[18px] border border-slate-900/10 bg-white/80 px-4 py-4 sm:flex-row sm:items-start"
          >
            <span className="leading-6 text-slate-800">{entry.message}</span>
            <time className="whitespace-nowrap text-sm text-slate-500">{formatTimestamp(entry.createdAt)}</time>
          </li>
        ))}
      </ol>
    </PanelShell>
  );
}
