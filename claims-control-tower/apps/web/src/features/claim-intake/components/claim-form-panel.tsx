import type { UseMutationResult } from "@tanstack/react-query";

import { PanelShell } from "./panel-shell";
import { ClaimSummaryCard } from "./claim-summary-card";
import type { ClaimResponse } from "@/types/api";
import type { ClaimFormState } from "../types";

type ClaimFormPanelProps = {
  form: ClaimFormState;
  readyToCreate: boolean;
  isResetPending: boolean;
  activeClaim: ClaimResponse | null;
  createClaimPending: boolean;
  onSubmit: (event: React.FormEvent<HTMLFormElement>) => Promise<void>;
  onChange: <Key extends keyof ClaimFormState>(key: Key, value: ClaimFormState[Key]) => void;
};

export function ClaimFormPanel({
  form,
  readyToCreate,
  isResetPending,
  activeClaim,
  createClaimPending,
  onSubmit,
  onChange
}: ClaimFormPanelProps) {
  return (
    <PanelShell eyebrow="Step 1" title="Create claim" status={isResetPending ? "Resetting" : "Ready"} testId="claim-form-panel">
      <form className="grid gap-4" onSubmit={onSubmit}>
        <label className="grid gap-2 font-semibold text-slate-900">
          Claim number
          <input
            className="w-full rounded-2xl border border-slate-900/15 bg-white/90 px-4 py-3 text-slate-900 outline-none transition focus:border-teal-700 focus:ring-2 focus:ring-teal-600/20"
            value={form.claimNumber}
            onChange={(event) => onChange("claimNumber", event.target.value)}
            placeholder="CLM-2026-001"
            required
          />
        </label>

        <div className="grid gap-4 md:grid-cols-2">
          <label className="grid gap-2 font-semibold text-slate-900">
            Customer id
            <input
              className="w-full rounded-2xl border border-slate-900/15 bg-white/90 px-4 py-3 text-slate-900 outline-none transition focus:border-teal-700 focus:ring-2 focus:ring-teal-600/20"
              value={form.customerId}
              onChange={(event) => onChange("customerId", event.target.value)}
              placeholder="1001"
              inputMode="numeric"
              required
            />
          </label>
          <label className="grid gap-2 font-semibold text-slate-900">
            Claim type
            <select
              className="w-full rounded-2xl border border-slate-900/15 bg-white/90 px-4 py-3 text-slate-900 outline-none transition focus:border-teal-700 focus:ring-2 focus:ring-teal-600/20"
              value={form.claimType}
              onChange={(event) => onChange("claimType", event.target.value)}
            >
              <option value="motor">Motor</option>
              <option value="travel">Travel</option>
              <option value="property">Property</option>
              <option value="medical">Medical</option>
              <option value="theft">Theft</option>
            </select>
          </label>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <label className="grid gap-2 font-semibold text-slate-900">
            Incident date
            <input
              className="w-full rounded-2xl border border-slate-900/15 bg-white/90 px-4 py-3 text-slate-900 outline-none transition focus:border-teal-700 focus:ring-2 focus:ring-teal-600/20"
              type="date"
              value={form.incidentDate}
              onChange={(event) => onChange("incidentDate", event.target.value)}
            />
          </label>
          <label className="grid gap-2 font-semibold text-slate-900">
            Claim amount
            <input
              className="w-full rounded-2xl border border-slate-900/15 bg-white/90 px-4 py-3 text-slate-900 outline-none transition focus:border-teal-700 focus:ring-2 focus:ring-teal-600/20"
              value={form.claimAmount}
              onChange={(event) => onChange("claimAmount", event.target.value)}
              placeholder="2400"
              inputMode="decimal"
            />
          </label>
        </div>

        <label className="grid gap-2 font-semibold text-slate-900">
          Description
          <textarea
            className="min-h-28 w-full resize-y rounded-2xl border border-slate-900/15 bg-white/90 px-4 py-3 text-slate-900 outline-none transition focus:border-teal-700 focus:ring-2 focus:ring-teal-600/20"
            value={form.description}
            onChange={(event) => onChange("description", event.target.value)}
            placeholder="Rear bumper damage after low-speed collision."
            rows={4}
          />
        </label>

        <button
          type="submit"
          className="rounded-2xl bg-gradient-to-br from-teal-700 to-emerald-500 px-5 py-3 font-bold text-white transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={!readyToCreate || createClaimPending}
        >
          {createClaimPending ? "Creating claim..." : "Create claim"}
        </button>
      </form>

      {activeClaim ? <ClaimSummaryCard claim={activeClaim} /> : null}
    </PanelShell>
  );
}
