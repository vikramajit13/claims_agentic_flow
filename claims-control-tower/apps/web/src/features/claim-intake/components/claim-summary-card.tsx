import { formatTimestamp } from "../lib/helpers";
import { StatusPill } from "./status-pill";
import type { ClaimResponse } from "@/types/api";

type ClaimSummaryCardProps = {
  claim: ClaimResponse;
};

export function ClaimSummaryCard({ claim }: ClaimSummaryCardProps) {
  return (
    <div className="mt-5 rounded-[22px] border border-slate-900/8 bg-white/92 p-5">
      <div className="flex flex-col items-start justify-between gap-3 sm:flex-row sm:items-center">
        <h3 className="text-base font-semibold text-slate-900">{claim.claim_number}</h3>
        <StatusPill value={claim.status} />
      </div>
      <dl className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
        <div className="rounded-2xl bg-slate-50/90 px-4 py-3">
          <dt className="mb-1 text-xs uppercase tracking-[0.08em] text-slate-500">Claim id</dt>
          <dd>{claim.id}</dd>
        </div>
        <div className="rounded-2xl bg-slate-50/90 px-4 py-3">
          <dt className="mb-1 text-xs uppercase tracking-[0.08em] text-slate-500">Customer</dt>
          <dd>{claim.customer_id}</dd>
        </div>
        <div className="rounded-2xl bg-slate-50/90 px-4 py-3">
          <dt className="mb-1 text-xs uppercase tracking-[0.08em] text-slate-500">Type</dt>
          <dd>{claim.claim_type}</dd>
        </div>
        <div className="rounded-2xl bg-slate-50/90 px-4 py-3">
          <dt className="mb-1 text-xs uppercase tracking-[0.08em] text-slate-500">Created</dt>
          <dd>{formatTimestamp(claim.created_at)}</dd>
        </div>
      </dl>
    </div>
  );
}
