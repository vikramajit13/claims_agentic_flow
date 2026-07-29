import clsx from "clsx";

type StatusPillProps = {
  value: string;
};

export function StatusPill({ value }: StatusPillProps) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full border px-3 py-2 text-xs font-bold capitalize",
        {
          "border-transparent bg-sky-600/12 text-sky-800":
            value === "draft" || value === "created" || value === "pending_upload" || value === "pending",
          "border-transparent bg-teal-600/12 text-teal-800":
            value === "submitted" ||
            value === "uploaded" ||
            value === "ready_for_graph" ||
            value === "completed" ||
            value === "ocr_completed",
          "border-transparent bg-amber-600/12 text-amber-800":
            value === "waiting_for_documents" || value === "ocr_queued" || value === "not_requested",
          "border-transparent bg-rose-700/12 text-rose-800":
            value === "waiting_for_human" || value === "failed"
        }
      )}
    >
      {value}
    </span>
  );
}
