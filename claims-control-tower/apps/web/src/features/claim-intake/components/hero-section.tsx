import { runtimeConfig } from "@/config/runtime";

export function HeroSection() {
  return (
    <section className="rounded-[30px] border border-slate-900/10 bg-[linear-gradient(135deg,rgba(255,255,255,0.82),rgba(252,247,238,0.92))] p-8 shadow-[0_22px_60px_rgba(24,45,66,0.12)] backdrop-blur-xl">
      <p className="mb-2 text-[0.74rem] font-bold uppercase tracking-[0.18em] text-teal-800">Claims Agentic Flow</p>
      <h1 className="max-w-[900px] text-[clamp(2.2rem,4vw,4.4rem)] font-semibold leading-[0.98] tracking-[-0.05em] text-slate-950">
        Claim intake, S3 document upload, and workflow bootstrap
      </h1>
      <p className="mt-5 max-w-[780px] text-base leading-7 text-slate-500">
        This web console creates a claim, requests pre-signed S3 uploads, sends files directly to your
        document bucket, confirms upload completion, and starts the backend workflow so you can stitch
        FastAPI, Lambda, SQS, and Textract together incrementally.
      </p>
      <div className="mt-6 inline-flex items-center gap-3 rounded-full border border-slate-900/10 bg-white/80 px-4 py-3">
        <span className="text-xs uppercase tracking-[0.12em] text-slate-500">API</span>
        <code className="font-mono text-sm text-slate-800">{runtimeConfig.apiBaseUrl}</code>
      </div>
    </section>
  );
}
