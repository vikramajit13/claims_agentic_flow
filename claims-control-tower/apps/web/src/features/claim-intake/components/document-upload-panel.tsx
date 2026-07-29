import { PanelShell } from "./panel-shell";
import { DocumentCard } from "./document-card";
import { inferRunOcr } from "../lib/helpers";
import type { ClaimDocumentResponse } from "@/types/api";

type DocumentUploadPanelProps = {
  hasActiveClaim: boolean;
  isUploading: boolean;
  isUploadLocked: boolean;
  isDragActive: boolean;
  selectedFiles: File[];
  activeUploads: string[];
  uploadProgress: Record<string, number>;
  queue: ClaimDocumentResponse[];
  onFileSelection: (event: React.ChangeEvent<HTMLInputElement>) => void;
  onDrop: (event: React.DragEvent<HTMLDivElement>) => void;
  onDragOver: (event: React.DragEvent<HTMLDivElement>) => void;
  onDragLeave: (event: React.DragEvent<HTMLDivElement>) => void;
  onUploadAll: () => Promise<void>;
  onClearSelected: () => void;
  onUploadSingle: (file: File) => Promise<void>;
};

export function DocumentUploadPanel({
  hasActiveClaim,
  isUploading,
  isUploadLocked,
  isDragActive,
  selectedFiles,
  activeUploads,
  uploadProgress,
  queue,
  onFileSelection,
  onDrop,
  onDragOver,
  onDragLeave,
  onUploadAll,
  onClearSelected,
  onUploadSingle
}: DocumentUploadPanelProps) {
  return (
    <PanelShell
      eyebrow="Step 2"
      title="Upload invoice and images"
      status={isUploading ? "Uploading" : "Idle"}
      testId="document-upload-panel"
    >
      <div
        className={`rounded-[24px] border border-dashed p-6 transition ${
          isDragActive
            ? "border-teal-700 bg-teal-600/12 ring-2 ring-teal-600/20"
            : "border-teal-700/35 bg-gradient-to-b from-teal-600/8 to-white/85"
        }`}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
      >
        <input
          className="block w-full text-sm text-slate-700 file:mr-4 file:rounded-full file:border-0 file:bg-slate-900 file:px-4 file:py-2 file:font-semibold file:text-white hover:file:bg-slate-700"
          type="file"
          multiple
          accept="image/*,.pdf"
          onChange={onFileSelection}
          disabled={!hasActiveClaim || isUploadLocked}
          data-testid="document-input"
        />
        <p className="mt-3 text-sm leading-6 text-slate-500">
          Select accident photos and invoice or estimate PDFs, or drag and drop them here. Images skip OCR in the current backend. PDFs request OCR.
        </p>
      </div>

      <div className="mt-5 grid gap-3">
        {selectedFiles.length === 0 ? <p className="text-sm leading-6 text-slate-500">No files selected yet.</p> : null}
        {selectedFiles.map((file) => (
          <div
            key={`${file.name}-${file.size}`}
            className="flex flex-col items-start justify-between gap-3 rounded-[18px] border border-slate-900/10 bg-white/80 px-4 py-4 sm:flex-row sm:items-center"
          >
            <div>
              <strong className="text-slate-900">{file.name}</strong>
              <p className="mt-1 text-sm text-slate-500">
                {file.type || "Unknown type"} · {(file.size / 1024).toFixed(1)} KB
              </p>
              {typeof uploadProgress[file.name] === "number" ? (
                <div className="mt-3 w-full max-w-sm">
                  <div className="h-2 overflow-hidden rounded-full bg-slate-200">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-teal-700 to-emerald-500 transition-[width]"
                      style={{ width: `${uploadProgress[file.name]}%` }}
                    />
                  </div>
                  <p className="mt-1 text-xs text-slate-500">
                    {activeUploads.includes(file.name) ? `Uploading ${uploadProgress[file.name]}%` : `Ready ${uploadProgress[file.name]}%`}
                  </p>
                </div>
              ) : null}
            </div>
            <span className="text-sm text-teal-800">{inferRunOcr(file) ? "OCR requested" : "Image upload only"}</span>
          </div>
        ))}
      </div>

      <div className="mt-5 flex flex-wrap gap-3">
        <button
          type="button"
          className="rounded-2xl bg-gradient-to-br from-teal-700 to-emerald-500 px-5 py-3 font-bold text-white transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-60"
          onClick={() => void onUploadAll()}
          disabled={!hasActiveClaim || selectedFiles.length === 0 || isUploadLocked}
          data-testid="upload-all-button"
        >
          {isUploading ? "Uploading files..." : isUploadLocked ? "Upload in progress..." : "Upload selected files"}
        </button>
        <button
          type="button"
          className="rounded-2xl border border-slate-900/10 bg-white/70 px-5 py-3 font-semibold text-slate-800 transition hover:bg-white"
          onClick={onClearSelected}
          disabled={selectedFiles.length === 0 || isUploadLocked}
        >
          Clear file list
        </button>
      </div>

      <div className="mt-6 grid gap-4">
        {queue.length === 0 ? (
          <p className="text-sm leading-6 text-slate-500">Uploaded claim documents will appear here once the claim is created.</p>
        ) : null}
        {queue.map((document) => (
          <DocumentCard
            key={document.id}
            document={document}
            onUpload={() => {
              if (isUploadLocked) {
                return;
              }
              const target = selectedFiles.find((file) => file.name === document.file_name);
              if (target) {
                void onUploadSingle(target);
              }
            }}
          />
        ))}
      </div>
    </PanelShell>
  );
}
