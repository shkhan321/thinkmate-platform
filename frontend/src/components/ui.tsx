import { useEffect, useRef, useState, type ReactNode } from "react";
import { REASONING_STEPS, studentProgress, tourSteps, type ReasoningNode, type StudentStage } from "../flow";
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
  const [open, setOpen] = useState(false);
  if (!bloom && !paulElder) return null;
  const tone = (bloom && bloomStyles[bloom.toLowerCase()]) || "bg-slate-100 text-slate-600";
  // Tappable (not hover-only) so the plain-language meaning is reachable on phones.
  return (
    <div className="mt-2">
      <div className="flex flex-wrap items-center gap-1.5">
        {bloom && (
          <button type="button" onClick={() => setOpen((v) => !v)} className={`tm-chip ${tone}`} aria-expanded={open}>
            {capitalize(bloom)}
          </button>
        )}
        {paulElder && (
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="tm-chip bg-slate-100 text-slate-600"
            aria-expanded={open}
          >
            {capitalize(paulElder)}
          </button>
        )}
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="text-xs text-slate-500 underline underline-offset-2"
        >
          {open ? "hide" : "what's this?"}
        </button>
      </div>
      {open && (
        <p className="mt-1 text-xs text-slate-600">
          {bloom && (
            <>
              <span className="font-semibold">{capitalize(bloom)}</span> — the thinking skill (Bloom's taxonomy).{" "}
            </>
          )}
          {paulElder && (
            <>
              <span className="font-semibold">{capitalize(paulElder)}</span> — the quality-of-reasoning standard (Paul–Elder).
            </>
          )}
        </p>
      )}
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

export function ReasoningTree({
  nodes,
  title = "Your reasoning tree",
  subtitle = "Built from your own answers — it grows as you go.",
  variant = "live"
}: {
  nodes: ReasoningNode[];
  title?: string;
  subtitle?: string;
  variant?: "live" | "keepsake";
}) {
  const doneCount = nodes.filter((node) => node.filled).length;
  const allDone = nodes.length > 0 && doneCount === nodes.length;
  // Render top-to-bottom so the foundation (claim) sits at the bottom and the
  // newest thinking (revise) is at the top — the tree builds upward.
  const topDown = [...nodes].reverse();
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  // Detect dimensions that newly filled and (a) one-shot "pop" them, (b) announce
  // them politely to screen readers — so the "watch your thinking grow" moment
  // lands for everyone. Keyed by the SET of filled dimensions (a stable string)
  // so re-renders from a new turns array don't retrigger.
  const filledSignature = nodes.filter((node) => node.filled).map((node) => node.key).join(",");
  const prevFilled = useRef<Set<string>>(new Set());
  const [popped, setPopped] = useState<Set<string>>(new Set());
  const [announce, setAnnounce] = useState("");
  useEffect(() => {
    const filledNow = new Set(filledSignature ? filledSignature.split(",") : []);
    const newly = [...filledNow].filter((key) => !prevFilled.current.has(key));
    prevFilled.current = filledNow;
    if (!newly.length) return;
    const last = nodes.find((node) => node.key === newly[newly.length - 1]);
    if (last) setAnnounce(`${last.label} added to your reasoning tree.`);
    setPopped(new Set(newly));
    const timer = window.setTimeout(() => setPopped(new Set()), 600);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filledSignature]);

  const emptyLabel = variant === "keepsake" ? "— not covered —" : "— your turn —";
  const titleId = "reasoning-tree-title";

  function toggle(key: string) {
    setExpanded((current) => {
      const next = new Set(current);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  }

  return (
    <div>
      <div className="flex items-center justify-between gap-2">
        <p id={titleId} className="text-sm font-bold text-slate-800">{title}</p>
        {allDone ? (
          <span className="tm-chip bg-emerald-100 text-emerald-700">
            <CheckIcon className="h-3 w-3" /> Complete
          </span>
        ) : (
          <span className="text-xs font-semibold text-brand-600">
            {doneCount}/{nodes.length}
          </span>
        )}
      </div>
      <p className="mt-0.5 text-xs text-slate-500">
        {allDone ? "Nicely built — every part of your reasoning is here." : subtitle}
      </p>
      <p className="mt-2 text-[11px] font-semibold text-slate-500">↑ your latest thinking</p>
      <ol className="mt-1 space-y-1.5" aria-labelledby={titleId}>
        {topDown.map((node, index) => {
          const tone = node.filled
            ? "border-emerald-200 bg-emerald-50"
            : node.current
              ? "border-brand-300 bg-brand-50 ring-1 ring-brand-200"
              : "border-dashed border-slate-200 bg-white";
          const labelTone = node.filled
            ? "text-emerald-700"
            : node.current
              ? "text-brand-700"
              : "text-slate-500";
          const isFoundation = index === topDown.length - 1;
          const isExpanded = variant === "keepsake" || expanded.has(node.key);
          const canExpand = variant === "live" && node.filled && node.full.length > node.answer.length;
          const popClass = variant === "live" && popped.has(node.key) ? " tm-pop" : "";
          return (
            <li key={node.key}>
              <div className={`min-w-0 rounded-2xl border p-3${popClass} ${tone}`}>
                <p className={`flex items-center gap-1 text-[11px] font-bold uppercase tracking-wide ${labelTone}`}>
                  {node.filled && <CheckIcon className="h-3 w-3" />}
                  {node.label}
                  {node.current && !node.filled && (
                    <span className="inline-flex items-center gap-1 font-semibold lowercase">
                      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-brand-500" aria-hidden="true" />
                      now
                    </span>
                  )}
                </p>
                {node.filled ? (
                  canExpand ? (
                    <button
                      type="button"
                      onClick={() => toggle(node.key)}
                      aria-expanded={isExpanded}
                      className="mt-0.5 block w-full break-words text-left text-sm font-semibold text-slate-800"
                    >
                      {isExpanded ? node.full : node.answer}
                      <span className="ml-1 text-xs font-normal text-brand-600">{isExpanded ? "show less" : "show full"}</span>
                    </button>
                  ) : (
                    <p className="mt-0.5 break-words text-sm font-semibold text-slate-800">
                      {isExpanded ? node.full : node.answer}
                    </p>
                  )
                ) : (
                  <p className="mt-0.5 text-sm text-slate-500">{emptyLabel}</p>
                )}
              </div>
              {!isFoundation && <div className="mx-auto h-3 w-0.5 bg-brand-200" aria-hidden="true" />}
            </li>
          );
        })}
      </ol>
      <p className="mt-1.5 text-[11px] font-semibold text-slate-500">start: your claim</p>
      <p className="sr-only" aria-live="polite">{announce}</p>
    </div>
  );
}

export function Callout({ children }: { children: ReactNode }) {
  return (
    <div role="alert" className="flex items-start gap-2 rounded-2xl bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">
      <span className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-rose-200 text-xs font-bold text-rose-700">
        !
      </span>
      <span>{children}</span>
    </div>
  );
}

export function QuickTour({ onClose }: { onClose: () => void }) {
  const steps = tourSteps();
  const panelRef = useRef<HTMLElement>(null);

  // Modal a11y: close on Escape, keep focus inside the dialog (focus trap),
  // and return focus to whatever opened it. (WCAG 2.1.2 + 2.4.7)
  useEffect(() => {
    const previouslyFocused = document.activeElement as HTMLElement | null;
    const focusables = () =>
      Array.from(
        panelRef.current?.querySelectorAll<HTMLElement>(
          'button, [href], input, textarea, select, [tabindex]:not([tabindex="-1"])'
        ) ?? []
      );
    focusables()[0]?.focus();

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
        return;
      }
      if (event.key === "Tab") {
        const items = focusables();
        if (items.length === 0) return;
        const first = items[0];
        const last = items[items.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    }

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      previouslyFocused?.focus?.();
    };
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-slate-900/40 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="tour-title"
      onClick={onClose}
    >
      <section
        ref={panelRef}
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
