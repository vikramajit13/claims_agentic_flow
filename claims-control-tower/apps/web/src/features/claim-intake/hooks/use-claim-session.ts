import { useCallback, useState } from "react";

import { getClaim } from "@/lib/http";
import { useClaimIntakeStore } from "@/store/claim-intake-store";
import type { ClaimResponse, WorkflowRunResponse } from "@/types/api";

export function useClaimSession() {
  const [activeClaim, setActiveClaim] = useState<ClaimResponse | null>(null);
  const [latestWorkflow, setLatestWorkflow] = useState<WorkflowRunResponse | null>(null);

  const { setClaim, setQueue, reset: resetStore } = useClaimIntakeStore();

  const hydrateClaim = useCallback(
    (claim: ClaimResponse | null) => {
      setActiveClaim(claim);
      setClaim(claim);
      setQueue(claim?.documents ?? []);
    },
    [setClaim, setQueue]
  );

  const refreshClaim = useCallback(
    async (claimId: number) => {
      const latest = await getClaim(claimId);
      hydrateClaim(latest);
      return latest;
    },
    [hydrateClaim]
  );

  function resetSession() {
    resetStore();
    setActiveClaim(null);
    setLatestWorkflow(null);
  }

  return {
    activeClaim,
    latestWorkflow,
    setLatestWorkflow,
    hydrateClaim,
    refreshClaim,
    resetSession
  };
}
