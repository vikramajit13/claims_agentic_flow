import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";

import { apiGet } from "@/lib/http";
import { useDashboardStore } from "@/store/dashboard-store";
import type { ClaimSummary } from "@/types";

interface ClaimApiResponse {
  id: number;
  claim_number: string;
  status: string;
  claim_type: string;
  customer_id: number;
}

function mapClaims(claims: ClaimApiResponse[]): ClaimSummary[] {
  return claims.map((claim) => ({
    id: claim.id,
    claimNumber: claim.claim_number,
    status: claim.status,
    claimType: claim.claim_type,
    customerId: claim.customer_id
  }));
}

export function useDashboardBootstrap() {
  const setClaims = useDashboardStore((state) => state.setClaims);

  const query = useQuery({
    queryKey: ["claims"],
    queryFn: () => apiGet<ClaimApiResponse[]>("/v1/claims")
  });

  useEffect(() => {
    if (query.data) {
      setClaims(mapClaims(query.data));
    }
  }, [query.data, setClaims]);

  return query;
}
