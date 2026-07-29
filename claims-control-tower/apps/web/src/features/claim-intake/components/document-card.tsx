import type { ClaimDocumentResponse } from "@/types/api";

import { formatTimestamp, readDocumentType } from "../lib/helpers";
import { StatusPill } from "./status-pill";

type DocumentCardProps = {
  document: ClaimDocumentResponse;
  onUpload: () => void;
};

export function DocumentCard({ document, onUpload }: DocumentCardProps) {
  return (
    <article className="rounded-[22px] border border-slate-900/8 bg-white/92 p-5">
      <div className="flex flex-col items-start justify-between gap-3 sm:flex-row">
        <div>
          <h4 className="text-base font-semibold text-slate-900">{document.file_name}</h4>
          <p className="mt-1 text-sm text-slate-500">{document.content_type ?? "Unknown content type"}</p>
        </div>
        <StatusPill value={document.upload_status} />
      </div>

      <dl className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
        <div className="rounded-2xl bg-slate-50/90 px-4 py-3">
          <dt className="mb-1 text-xs uppercase tracking-[0.08em] text-slate-500">OCR</dt>
          <dd>{document.ocr_status}</dd>
        </div>
        <div className="rounded-2xl bg-slate-50/90 px-4 py-3">
          <dt className="mb-1 text-xs uppercase tracking-[0.08em] text-slate-500">Document type</dt>
          <dd>{readDocumentType(document)}</dd>
        </div>
        <div className="rounded-2xl bg-slate-50/90 px-4 py-3">
          <dt className="mb-1 text-xs uppercase tracking-[0.08em] text-slate-500">Updated</dt>
          <dd>{formatTimestamp(document.updated_at)}</dd>
        </div>
      </dl>

      <div className="mt-4 flex flex-col items-start justify-between gap-3 lg:flex-row lg:items-center">
        <code className="block break-all font-mono text-xs text-slate-500">{document.s3_uri}</code>
        {document.upload_status === "pending_upload" ? (
          <button
            type="button"
            className="rounded-2xl bg-gradient-to-br from-sky-700 to-cyan-500 px-4 py-3 font-bold text-white transition hover:-translate-y-0.5"
            onClick={onUpload}
          >
            Upload to S3
          </button>
        ) : null}
      </div>
    </article>
  );
}
