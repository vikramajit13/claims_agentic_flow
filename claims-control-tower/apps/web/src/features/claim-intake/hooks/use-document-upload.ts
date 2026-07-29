import { useCallback, useEffect, useMemo, useState } from "react";

import { completeDocumentUpload, createDocumentPresign } from "@/lib/http";
import { useClaimIntakeStore } from "@/store/claim-intake-store";
import type { ClaimResponse } from "@/types/api";

import { inferRunOcr } from "../lib/helpers";

type UseDocumentUploadOptions = {
  activeClaim: ClaimResponse | null;
  refreshClaim: (claimId: number) => Promise<ClaimResponse>;
};

export function useDocumentUpload(options: UseDocumentUploadOptions) {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [activeUploads, setActiveUploads] = useState<string[]>([]);
  const [isDragActive, setIsDragActive] = useState(false);

  const {
    isUploading,
    queue,
    uploadProgress,
    setUploading,
    setUploadProgress,
    clearUploadProgress,
    addLog,
    updateQueueDocument
  } = useClaimIntakeStore();

  useEffect(() => {
    setUploading(activeUploads.length > 0);
  }, [activeUploads.length, setUploading]);

  const isUploadLocked = useMemo(() => {
    return isUploading || activeUploads.length > 0;
  }, [activeUploads.length, isUploading]);

  const mergeFiles = useCallback((files: File[]) => {
    setSelectedFiles((current) => {
      const next = new Map(current.map((file) => [`${file.name}-${file.size}`, file]));
      files.forEach((file) => next.set(`${file.name}-${file.size}`, file));
      return Array.from(next.values());
    });
  }, []);

  const uploadFileWithProgress = useCallback(
    (file: File, uploadUrl: string, method: string, headers: Record<string, string>) =>
      new Promise<void>((resolve, reject) => {
        const request = new XMLHttpRequest();
        request.open(method, uploadUrl);

        Object.entries(headers).forEach(([key, value]) => {
          request.setRequestHeader(key, value);
        });

        request.upload.onprogress = (event) => {
          if (!event.lengthComputable) {
            return;
          }
          setUploadProgress(file.name, Math.round((event.loaded / event.total) * 100));
        };

        request.onload = () => {
          if (request.status >= 200 && request.status < 300) {
            setUploadProgress(file.name, 100);
            resolve();
            return;
          }
          reject(new Error(`S3 upload failed for ${file.name}: ${request.status}`));
        };

        request.onerror = () => {
          reject(new Error(`S3 upload failed for ${file.name}: network error`));
        };

        request.send(file);
      }),
    [setUploadProgress]
  );

  const uploadFileForClaim = useCallback(
    async (file: File) => {
      const claim = options.activeClaim;
      if (!claim) {
        throw new Error("Create a claim before uploading documents.");
      }
      if (activeUploads.includes(file.name)) {
        return;
      }

      setActiveUploads((current) => [...current, file.name]);
      setUploadProgress(file.name, 0);
      addLog(`Preparing ${file.name} for upload.`);

      try {
        const presign = await createDocumentPresign(claim.id, {
          file_name: file.name,
          content_type: file.type || "application/octet-stream",
          run_ocr: inferRunOcr(file)
        });

        addLog(`Presigned upload created for ${file.name}. Uploading to S3.`);

        await uploadFileWithProgress(file, presign.upload_url, presign.upload_method, presign.upload_headers);

        const completed = await completeDocumentUpload(claim.id, presign.document_id, {});
        updateQueueDocument(completed);
        addLog(`Upload completed for ${file.name}. OCR status: ${completed.ocr_status}.`);

        await options.refreshClaim(claim.id);
      } finally {
        setActiveUploads((current) => current.filter((entry) => entry !== file.name));
        clearUploadProgress(file.name);
      }
    },
    [
      activeUploads,
      addLog,
      clearUploadProgress,
      options,
      setUploadProgress,
      updateQueueDocument,
      uploadFileWithProgress
    ]
  );

  function handleFileSelection(event: React.ChangeEvent<HTMLInputElement>) {
    mergeFiles(Array.from(event.target.files ?? []));
  }

  function handleDragOver(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    if (!Array.from(event.dataTransfer.items ?? []).some((item) => item.kind === "file")) {
      return;
    }
    setIsDragActive(true);
  }

  function handleDragLeave(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    if (event.currentTarget.contains(event.relatedTarget as Node | null)) {
      return;
    }
    setIsDragActive(false);
  }

  function handleDropEvent(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    mergeFiles(Array.from(event.dataTransfer.files ?? []));
    setIsDragActive(false);
  }

  async function handleUploadAll() {
    if (isUploadLocked || selectedFiles.length === 0) {
      return;
    }
    for (const file of selectedFiles) {
      await uploadFileForClaim(file);
    }
    setSelectedFiles([]);
  }

  return {
    selectedFiles,
    setSelectedFiles,
    activeUploads,
    isDragActive,
    isUploading,
    isUploadLocked,
    uploadProgress,
    queue,
    handleFileSelection,
    handleDragOver,
    handleDragLeave,
    handleDropEvent,
    handleUploadAll,
    uploadFileForClaim
  };
}
