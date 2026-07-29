import { useMemo, useTransition } from "react";

import { createClaim } from "@/lib/http";
import { useClaimIntakeStore } from "@/store/claim-intake-store";
import { useAsyncTask } from "@/hooks/base/use-async-task";
import { useFormState } from "@/hooks/base/use-form-state";
import type { ClaimResponse } from "@/types/api";

import { buildClaimPayload } from "../lib/helpers";
import { initialClaimFormState, type ClaimFormState } from "../types";

type ClaimFormOptions = {
  onClaimCreated: (claim: ClaimResponse) => void;
  onBeforeSubmit: () => void;
};

export function useClaimForm(options: ClaimFormOptions) {
  const [isResetPending, startTransition] = useTransition();
  const { addLog } = useClaimIntakeStore();
  const form = useFormState<ClaimFormState>(initialClaimFormState);

  const createClaimTask = useAsyncTask(async (payload: ClaimFormState) => {
    options.onBeforeSubmit();
    const claim = await createClaim(buildClaimPayload(payload));
    options.onClaimCreated(claim);
    addLog(`Claim ${claim.claim_number} created with id ${claim.id}.`);
    return claim;
  });

  const readyToCreate = useMemo(() => {
    return Boolean(
      form.state.claimNumber.trim() &&
        form.state.customerId.trim() &&
        form.state.claimType.trim()
    );
  }, [form.state]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!readyToCreate || createClaimTask.isPending) {
      return;
    }

    await createClaimTask.run(form.state);
  }

  function resetForm() {
    startTransition(() => {
      form.reset(initialClaimFormState);
    });
  }

  return {
    formState: form.state,
    updateForm: form.updateField,
    handleSubmit,
    resetForm,
    readyToCreate,
    isResetPending,
    isCreatingClaim: createClaimTask.isPending
  };
}
