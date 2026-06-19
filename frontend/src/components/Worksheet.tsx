import { useMemo, useState } from "react";
import { api } from "../api";
import { canSubmitWorksheet, conditionTitle } from "../flow";
import type { PilotSession, PilotTask } from "../types";
import { Callout } from "./ui";
import { ClipboardIcon } from "./icons";

export function Worksheet({
  task,
  session,
  onFinish
}: {
  task: PilotTask;
  session: PilotSession;
  onFinish: () => Promise<void> | void;
}) {
  const [responses, setResponses] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const stepKeys = useMemo(() => task.worksheet_steps.map((step) => step.key), [task]);
  const completedCount = stepKeys.filter((key) => (responses[key] || "").trim().length > 0).length;
  const ready = canSubmitWorksheet(stepKeys, responses);
  const progress = stepKeys.length ? Math.round((completedCount / stepKeys.length) * 100) : 0;

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
      <aside className="tm-card h-fit p-5">
        <span className="tm-chip bg-accent-50 text-accent-600">
          <ClipboardIcon className="h-3.5 w-3.5" /> {conditionTitle("worksheet")}
        </span>
        <h2 className="mt-3 text-lg font-extrabold text-slate-900">{task.title}</h2>
        <p className="mt-1 text-sm leading-relaxed text-slate-600">{task.scenario}</p>

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

      <section className="tm-card p-5 sm:p-6">
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
                  placeholder="Write your answer here…"
                />
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
