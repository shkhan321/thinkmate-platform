import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { canSubmitWorksheet, conditionTitle } from "../flow";
import type { PilotSession, PilotTask } from "../types";
import { Callout } from "./ui";
import { ArrowLeftIcon, ClipboardIcon } from "./icons";

export function Worksheet({
  task,
  session,
  projectTitle,
  projectGoal,
  onFinish,
  onBack
}: {
  task: PilotTask;
  session: PilotSession;
  projectTitle?: string | null;
  projectGoal?: string | null;
  onFinish: () => Promise<void> | void;
  onBack: () => void;
}) {
  const [responses, setResponses] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  // Resume any answers the student already saved for this worksheet.
  useEffect(() => {
    let active = true;
    api
      .sessionState(session.id)
      .then((state) => {
        if (!active || state.worksheet_responses.length === 0) return;
        setResponses((current) => {
          const restored = { ...current };
          for (const row of state.worksheet_responses) {
            if (!(restored[row.step_key] ?? "").trim()) restored[row.step_key] = row.response;
          }
          return restored;
        });
      })
      .catch(() => {
        /* a fresh worksheet simply has no saved answers yet */
      });
    return () => {
      active = false;
    };
  }, [session.id]);

  const stepKeys = useMemo(() => task.worksheet_steps.map((step) => step.key), [task]);
  const completedCount = stepKeys.filter((key) => (responses[key] || "").trim().length > 0).length;
  const ready = canSubmitWorksheet(stepKeys, responses);
  const progress = stepKeys.length ? Math.round((completedCount / stepKeys.length) * 100) : 0;

  function handleBack() {
    const hasTyped = Object.values(responses).some((value) => value.trim().length > 0);
    if (hasTyped && !window.confirm("Leave this worksheet? Your answers here are not saved until you submit.")) {
      return;
    }
    onBack();
  }

  async function submit() {
    setBusy(true);
    setError("");
    try {
      for (const step of task.worksheet_steps) {
        await api.worksheetResponse(session.id, step.key, step.prompt, responses[step.key]);
      }
      await onFinish();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit your worksheet. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="tm-rise grid gap-4 lg:grid-cols-[320px_1fr]">
      <aside className="tm-card order-2 h-fit p-5 lg:order-1">
        <button type="button" className="tm-btn-ghost mb-3 !px-3 !py-1.5 text-xs" onClick={handleBack}>
          <ArrowLeftIcon className="h-4 w-4" /> Back to activities
        </button>
        <span className="tm-chip bg-accent-50 text-accent-600">
          <ClipboardIcon className="h-3.5 w-3.5" /> {conditionTitle("worksheet")}
        </span>
        <h2 className="mt-3 text-lg font-extrabold text-slate-900">{task.title}</h2>
        {projectTitle ? (
          <div className="mt-3 rounded-2xl border border-accent-200 bg-accent-50/50 p-3">
            <p className="text-xs font-bold uppercase tracking-wide text-accent-600">Your project</p>
            <p className="mt-0.5 text-sm font-semibold text-slate-800">{projectTitle}</p>
            {projectGoal && <p className="mt-0.5 text-xs text-slate-600">{projectGoal}</p>}
          </div>
        ) : (
          <p className="mt-1 text-sm leading-relaxed text-slate-600">{task.scenario}</p>
        )}

        <div className="mt-4 rounded-2xl bg-slate-50 p-4">
          <p className="text-sm font-bold text-slate-800">What to do</p>
          <p className="mt-1 text-sm text-slate-600">
            Complete each box in your own words. You can submit once every box has an answer.
          </p>
        </div>

        <div className="mt-4">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500">
            <span>{completedCount} of {stepKeys.length} boxes</span>
            <span>{progress}%</span>
          </div>
          <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-gradient-to-r from-brand-500 to-accent-500 transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </aside>

      <section className="tm-card order-1 p-5 sm:p-6 lg:order-2">
        <h2 className="text-lg font-extrabold text-slate-900">Your worksheet</h2>
        <p className="mt-1 text-sm text-slate-600">Work through each reasoning step in order.</p>

        {error && (
          <div className="mt-4">
            <Callout>{error}</Callout>
          </div>
        )}

        <div className="mt-5 space-y-5">
          {task.worksheet_steps.map((step, index) => {
            const filled = (responses[step.key] || "").trim().length > 0;
            return (
              <div key={step.key}>
                <label className="flex items-start gap-3">
                  <span
                    className={`mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full text-xs font-bold ${
                      filled ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-500"
                    }`}
                  >
                    {index + 1}
                  </span>
                  <span>
                    <span className="block font-bold text-slate-900">{step.label}</span>
                    <span className="block text-sm text-slate-600">{step.prompt}</span>
                  </span>
                </label>
                <textarea
                  className="tm-input mt-2 min-h-[5.5rem] resize-y"
                  value={responses[step.key] || ""}
                  onChange={(event) =>
                    setResponses((current) => ({ ...current, [step.key]: event.target.value }))
                  }
                  placeholder={step.example || "Write your answer here…"}
                />
                {step.example && (
                  <p className="mt-1 pl-10 text-xs text-slate-400">Stuck? {step.example}</p>
                )}
              </div>
            );
          })}
        </div>

        <button className="tm-btn-primary mt-6 w-full sm:w-auto" disabled={!ready || busy} onClick={submit}>
          {busy ? "Submitting…" : "Submit worksheet"}
        </button>
      </section>
    </div>
  );
}
