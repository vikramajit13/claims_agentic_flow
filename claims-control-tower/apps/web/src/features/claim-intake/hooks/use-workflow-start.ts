import { startWorkflow } from "@/lib/http";
import { useAsyncTask } from "@/hooks/base/use-async-task";
import { useClaimIntakeStore } from "@/store/claim-intake-store";
import type { ClaimResponse, WorkflowRunResponse } from "@/types/api";

type UseWorkflowStartOptions = {
  activeClaim: ClaimResponse | null;
  onWorkflowStarted: (workflow: WorkflowRunResponse) => void;
  refreshClaim: (claimId: number) => Promise<ClaimResponse>;
};

export function useWorkflowStart(options: UseWorkflowStartOptions) {
  const { addLog } = useClaimIntakeStore();

  const startTask = useAsyncTask(async () => {
    const claim = options.activeClaim;
    if (!claim) {
      throw new Error("Create a claim before starting the workflow.");
    }

    const workflow = await startWorkflow(claim.id, {
      hitl_required: false,
      notes: ["Started from web intake console"]
    });

    options.onWorkflowStarted(workflow);
    addLog(`Workflow ${workflow.id} started in step ${workflow.current_step}.`);
    await options.refreshClaim(claim.id);
    return workflow;
  });

  return {
    handleStartWorkflow: startTask.run,
    isStartingWorkflow: startTask.isPending
  };
}
