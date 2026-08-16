import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { listHumanReviews, resumeHumanReview } from "@/lib/http";
import type { ClaimResponse, HumanReviewResponse } from "@/types/api";

import { formatTimestamp } from "../lib/helpers";
import { PanelShell } from "./panel-shell";

type HumanReviewInboxPanelProps = {
  activeClaim: ClaimResponse | null;
  onReviewResolved?: () => Promise<void> | void;
};

export function HumanReviewInboxPanel({ activeClaim, onReviewResolved }: HumanReviewInboxPanelProps) {
  const queryClient = useQueryClient();
  const reviewsQuery = useQuery({
    queryKey: ["human-reviews", "pending"],
    queryFn: () => listHumanReviews("pending"),
    refetchInterval: 10000
  });

  const resumeMutation = useMutation({
    mutationFn: ({ reviewId, decision }: { reviewId: number; decision: string }) =>
      resumeHumanReview(reviewId, {
        decision,
        notes: `Resolved from UI with decision: ${decision}`
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["human-reviews", "pending"] });
      if (activeClaim) {
        await queryClient.invalidateQueries({ queryKey: ["claim-trace", activeClaim.id] });
      }
      await onReviewResolved?.();
    }
  });

  const reviews = reviewsQuery.data ?? [];

  return (
    <PanelShell
      eyebrow="HITL inbox"
      title="Pending human reviews"
      status={reviewsQuery.isFetching ? "Refreshing" : `${reviews.length} pending`}
      description="Persisted review checkpoints from Postgres-backed graph runs."
      testId="human-review-inbox-panel"
    >
      <div className="grid gap-3">
        {reviews.length === 0 ? (
          <div className="rounded-[18px] border border-dashed border-slate-900/12 bg-white/70 px-4 py-5 text-sm text-slate-500">
            No pending reviews right now.
          </div>
        ) : null}
        {reviews.map((review) => (
          <ReviewCard
            key={review.id}
            review={review}
            isActiveClaim={activeClaim?.id === review.claim_id}
            isPending={resumeMutation.isPending}
            onResolve={(decision) => resumeMutation.mutate({ reviewId: review.id, decision })}
          />
        ))}
      </div>
    </PanelShell>
  );
}

function ReviewCard({
  review,
  isActiveClaim,
  isPending,
  onResolve
}: {
  review: HumanReviewResponse;
  isActiveClaim: boolean;
  isPending: boolean;
  onResolve: (decision: string) => void;
}) {
  return (
    <div
      className={`rounded-[22px] border px-4 py-4 ${isActiveClaim ? "border-amber-300 bg-amber-50/70" : "border-slate-900/10 bg-white/80"}`}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-slate-900">Review #{review.id}</h3>
          <p className="text-sm text-slate-500">Claim {review.claim_id} · {review.review_mode}</p>
        </div>
        <span className="rounded-full border border-slate-900/10 bg-white px-3 py-1 text-xs uppercase tracking-[0.12em] text-slate-600">
          {review.status}
        </span>
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-700">
        {String(review.request_payload.message ?? "Human review requested.")}
      </p>
      <div className="mt-3 text-xs text-slate-500">Updated {formatTimestamp(review.updated_at)}</div>
      <div className="mt-4 flex flex-wrap gap-3">
        <button
          type="button"
          className="rounded-2xl bg-teal-700 px-4 py-2 font-semibold text-white disabled:opacity-60"
          disabled={isPending}
          onClick={() => onResolve("approve")}
        >
          Approve
        </button>
        <button
          type="button"
          className="rounded-2xl border border-slate-900/10 bg-white px-4 py-2 font-semibold text-slate-800 disabled:opacity-60"
          disabled={isPending}
          onClick={() => onResolve("reject")}
        >
          Reject
        </button>
      </div>
    </div>
  );
}
