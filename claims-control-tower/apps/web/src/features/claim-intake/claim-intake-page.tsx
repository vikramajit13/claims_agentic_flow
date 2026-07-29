import { ActivityLogPanel } from "./components/activity-log-panel";
import { ClaimFormPanel } from "./components/claim-form-panel";
import { DocumentUploadPanel } from "./components/document-upload-panel";
import { HeroSection } from "./components/hero-section";
import { WorkflowPanel } from "./components/workflow-panel";
import { useClaimIntakeStore } from "@/store/claim-intake-store";
import { useClaimForm } from "./hooks/use-claim-form";
import { useClaimSession } from "./hooks/use-claim-session";
import { useDocumentUpload } from "./hooks/use-document-upload";
import { useWorkflowStart } from "./hooks/use-workflow-start";

export function ClaimIntakePage() {
  const { activityLog } = useClaimIntakeStore();
  const session = useClaimSession();
  const claimForm = useClaimForm({
    onClaimCreated: session.hydrateClaim,
    onBeforeSubmit: () => {
      session.resetSession();
    }
  });
  const documentUpload = useDocumentUpload({
    activeClaim: session.activeClaim,
    refreshClaim: session.refreshClaim
  });
  const workflowStart = useWorkflowStart({
    activeClaim: session.activeClaim,
    onWorkflowStarted: session.setLatestWorkflow,
    refreshClaim: session.refreshClaim
  });

  return (
    <main className="mx-auto max-w-[1440px] px-5 py-8 sm:px-6 lg:px-8">
      <HeroSection />

      <section className="mt-6 grid gap-5 xl:grid-cols-[1.1fr_1fr]">
        <ClaimFormPanel
          form={claimForm.formState}
          readyToCreate={claimForm.readyToCreate}
          isResetPending={claimForm.isResetPending}
          activeClaim={session.activeClaim}
          createClaimPending={claimForm.isCreatingClaim}
          onSubmit={claimForm.handleSubmit}
          onChange={claimForm.updateForm}
        />
        <DocumentUploadPanel
          hasActiveClaim={Boolean(session.activeClaim)}
          isUploading={documentUpload.isUploading}
          isUploadLocked={documentUpload.isUploadLocked}
          isDragActive={documentUpload.isDragActive}
          selectedFiles={documentUpload.selectedFiles}
          activeUploads={documentUpload.activeUploads}
          uploadProgress={documentUpload.uploadProgress}
          queue={documentUpload.queue}
          onFileSelection={documentUpload.handleFileSelection}
          onDrop={documentUpload.handleDropEvent}
          onDragOver={documentUpload.handleDragOver}
          onDragLeave={documentUpload.handleDragLeave}
          onUploadAll={documentUpload.handleUploadAll}
          onClearSelected={() => documentUpload.setSelectedFiles([])}
          onUploadSingle={documentUpload.uploadFileForClaim}
        />
      </section>

      <section className="mt-6 grid gap-5 xl:grid-cols-2">
        <WorkflowPanel
          activeClaim={session.activeClaim}
          latestWorkflow={session.latestWorkflow}
          isStarting={workflowStart.isStartingWorkflow}
          onStartWorkflow={workflowStart.handleStartWorkflow}
          onResetSession={() => {
            session.resetSession();
            claimForm.resetForm();
            documentUpload.setSelectedFiles([]);
          }}
        />
        <ActivityLogPanel entries={activityLog} />
      </section>
    </main>
  );
}
