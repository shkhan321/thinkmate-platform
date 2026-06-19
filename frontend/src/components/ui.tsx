import type { ReactNode } from "react";
import { REASONING_STEPS, studentProgress, tourSteps, type StudentStage } from "../flow";
import { CheckIcon, CloseIcon, SparkIcon } from "./icons";

export function BrandMark({ size = "md" }: { size?: "sm" | "md" | "lg" }) {
  const box =
    size === "lg" ? "h-12 w-12" : size === "sm" ? "h-8 w-8" : "h-10 w-10";
  const icon = size === "lg" ? "h-7 w-7" : size === "sm" ? "h-4.5 w-4.5" : "h-5.5 w-5.5";
  return (
    <span
      className={`grid ${box} place-items-center rounded-2xl bg-gradient-to-br from-brand-500 to-accent-500 text-white shadow-lg shadow-brand-500/30`}
      aria-hidden="true"
    >
      <SparkIcon className={icon} />
    </span>
  );
}

export function Wordmark({ tagline = true }: { tagline?: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <BrandMark />
      <div className="leading-tight">
        <p className="text-lg font-extrabold tracking-tight text-slate-900">ThinkMate</p>
        {tagline && <p className="text-xs font-medium text-slate-500">Think it through</p>}
      </div>
    </div>
  );
}

export function Stepper({ stage }: { stage: StudentStage }) {
  const steps = studentProgress(stage);
  return (
    <ol className="flex flex-wrap items-center gap-x-2 gap-y-3">
      {steps.map((step, index) => {
        const isLast = index === steps.length - 1;
        const dot =
          step.status === "complete"
            ? "bg-brand-600 text-white"
            : step.status === "current"
              ? "bg-white text-brand-700 ring-2 ring-brand-500"
              : "bg-white text-slate-400 ring-1 ring-slate-200";
        const text =
          step.status === "upcoming" ? "text-slate-400" : "text-slate-700";
        return (
          <li key={step.label} className="flex items-center gap-2">
            <span className={`grid h-7 w-7 place-items-center rounded-full text-xs font-bold ${dot}`}>
              {step.status === "complete" ? <CheckIcon className="h-4 w-4" /> : index + 1}
            </span>
            <span className={`text-xs font-semibold sm:text-sm ${text}`}>{step.label}</span>
            {!isLast && <span className="mx-1 hidden h-px w-6 bg-slate-200 sm:block" />}
          </li>
        );
      })}
    </ol>
  );
}

const bloomStyles: Record<string, string> = {
  remember: "bg-sky-50 text-sky-700",
  understand: "bg-sky-50 text-sky-700",
  apply: "bg-teal-50 text-teal-700",
  analyze: "bg-indigo-50 text-indigo-700",
  evaluate: "bg-violet-50 text-violet-700",
  create: "bg-fuchsia-50 text-fuchsia-700"
};

export function PedagogyTags({
  bloom,
  paulElder
}: {
  bloom?: string | null;
  paulElder?: string | null;
}) {
  if (!bloom && !paulElder) return null;
  const tone = (bloom && bloomStyles[bloom.toLowerCase()]) || "bg-slate-100 text-slate-600";
  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      {bloom && <span className={`tm-chip ${tone}`}>{capitalize(bloom)}</span>}
      {paulElder && <span className="tm-chip bg-slate-100 text-slate-600">{capitalize(paulElder)}</span>}
    </div>
  );
}

export function ReasoningMap({
  covered,
  currentKey
}: {
  covered: Set<string>;
  currentKey: string | null;
}) {
  const doneCount = REASONING_STEPS.filter((step) => covered.has(step.key)).length;
  return (
    <div>
      <div className="flex items-center justify-between">
        <p className="text-sm font-bold text-slate-800">Your thinking map</p>
        <span className="text-xs font-semibold text-brand-600">{doneCount}/{REASONING_STEPS.length}</span>
      </div>
      <p className="mt-0.5 text-xs text-slate-500">How your reasoning is building.</p>
      <ol className="relative mt-3 space-y-3">
        {REASONING_STEPS.map((step, index) => {
          const isDone = covered.has(step.key);
          const isCurrent = !isDone && step.key === currentKey;
          const dot = isDone
            ? "bg-brand-600 text-white"
            : isCurrent
              ? "bg-brand-50 text-brand-700 ring-2 ring-brand-500"
              : "bg-white text-slate-300 ring-1 ring-slate-200";
          const last = index === REASONING_STEPS.length - 1;
          return (
            <li key={step.key} className="flex gap-3">
              <div className="flex flex-col items-center">
                <span className={`grid h-6 w-6 place-items-center rounded-full text-[11px] font-bold ${dot}`}>
                  {isDone ? <CheckIcon className="h-3.5 w-3.5" /> : index + 1}
                </span>
                {!last && <span className={`mt-1 w-px flex-1 ${isDone ? "bg-brand-200" : "bg-slate-200"}`} />}
              </div>
              <div className="-mt-0.5 pb-1">
                <p className={`text-sm font-semibold ${isDone || isCurrent ? "text-slate-800" : "text-slate-400"}`}>
                  {step.label}
                </p>
                <p className="text-xs text-slate-400">{step.hint}</p>
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

export function Callout({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-start gap-2 rounded-2xl bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">
      <span className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-rose-200 text-xs font-bold text-rose-700">
        !
      </span>
      <span>{children}</span>
    </div>
  );
}

export function QuickTour({ onClose }: { onClose: () => void }) {
  const steps = tourSteps();
  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-slate-900/40 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="tour-title"
      onClick={onClose}
    >
      <section
        className="tm-card tm-rise w-full max-w-lg p-6 sm:p-7"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-brand-600">Quick tour</p>
            <h2 id="tour-title" className="mt-1 text-xl font-extrabold text-slate-900">
              How ThinkMate works
            </h2>
          </div>
          <button className="tm-btn-ghost px-2.5 py-2" type="button" onClick={onClose} aria-label="Close tour">
            <CloseIcon className="h-4 w-4" />
          </button>
        </div>
        <ol className="space-y-3">
          {steps.map((step, index) => (
            <li key={step.title} className="flex gap-3 rounded-2xl bg-slate-50 p-3.5">
              <span className="grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-brand-600 text-sm font-bold text-white">
                {index + 1}
              </span>
              <div>
                <h3 className="font-bold text-slate-900">{step.title}</h3>
                <p className="text-sm text-slate-600">{step.body}</p>
              </div>
            </li>
          ))}
        </ol>
        <button className="tm-btn-primary mt-5 w-full" type="button" onClick={onClose}>
          Got it
        </button>
      </section>
    </div>
  );
}

function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}
