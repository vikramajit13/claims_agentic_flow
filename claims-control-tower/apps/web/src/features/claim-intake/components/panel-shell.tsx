import type { PropsWithChildren, ReactNode } from "react";

type PanelShellProps = PropsWithChildren<{
  eyebrow: string;
  title: string;
  status: ReactNode;
  description?: string;
  testId?: string;
}>;

export function PanelShell({ eyebrow, title, status, description, children, testId }: PanelShellProps) {
  return (
    <article
      className="rounded-[28px] border border-slate-900/10 bg-white/75 p-6 shadow-[0_22px_60px_rgba(24,45,66,0.12)] backdrop-blur-xl"
      data-testid={testId}
    >
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <p className="mb-2 text-[0.74rem] font-bold uppercase tracking-[0.18em] text-teal-800">{eyebrow}</p>
          <h2 className="text-[1.4rem] font-semibold tracking-[-0.03em] text-slate-900">{title}</h2>
          {description ? <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-500">{description}</p> : null}
        </div>
        <span className="inline-flex whitespace-nowrap rounded-full border border-slate-900/10 bg-white/85 px-3 py-2 text-sm text-slate-500">
          {status}
        </span>
      </div>
      {children}
    </article>
  );
}
