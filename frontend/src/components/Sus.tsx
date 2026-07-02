import { useState } from "react";
import { api } from "../api";
import { SUS_ITEMS } from "../flow";
import { Callout } from "./ui";

/** The 10-item System Usability Scale, shown once after the student's final
 * activity. One screen, ~90 seconds; the backend stores one row per student
 * (a re-submit updates it). The done-flag lives in localStorage per student so
 * the survey never nags on later visits. */
export function SusSurvey({ studentId }: { studentId: string }) {
  const storageKey = `thinkmate.sus.${studentId}`;
  const [done, setDone] = useState(() => {
    try {
      return window.localStorage.getItem(storageKey) === "1";
    } catch {
      return false;
    }
  });
  const [answers, setAnswers] = useState<Array<number | null>>(() => SUS_ITEMS.map(() => null));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const allAnswered = answers.every((value) => value !== null);

  function setAnswer(index: number, value: number) {
    setAnswers((current) => current.map((existing, i) => (i === index ? value : existing)));
  }

  async function submit() {
    if (!allAnswered || busy) return;
    setBusy(true);
    setError("");
    try {
      await api.submitSus(studentId, answers as number[]);
      try {
        window.localStorage.setItem(storageKey, "1");
      } catch {
        /* private mode: still hide the form for this view */
      }
      setDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not send your answers. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <div className="tm-card p-5 text-center">
        <p className="text-sm font-semibold text-slate-700">Thanks — your answers really help the study 🙏</p>
      </div>
    );
  }

  return (
    <div className="tm-card p-5 text-left">
      <p className="text-sm font-extrabold text-slate-900">One last thing — 10 quick questions</p>
      <p className="mt-0.5 text-xs text-slate-500">
        About a minute. For each statement, 1 = strongly disagree and 5 = strongly agree.
      </p>

      {error && (
        <div className="mt-3">
          <Callout>{error}</Callout>
        </div>
      )}

      <ol className="mt-4 space-y-4">
        {SUS_ITEMS.map((item, index) => (
          <li key={item}>
            <p className="text-sm font-semibold text-slate-800">
              {index + 1}. {item}
            </p>
            <div
              role="radiogroup"
              aria-label={item}
              className="mt-1.5 flex items-center gap-1.5"
            >
              <span className="mr-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">Disagree</span>
              {[1, 2, 3, 4, 5].map((value) => {
                const selected = answers[index] === value;
                return (
                  <button
                    key={value}
                    type="button"
                    role="radio"
                    aria-checked={selected}
                    aria-label={`${value} of 5`}
                    onClick={() => setAnswer(index, value)}
                    className={`grid h-9 w-9 place-items-center rounded-xl border text-sm font-bold transition ${
                      selected
                        ? "border-brand-500 bg-brand-600 text-white"
                        : "border-slate-200 bg-white text-slate-600 hover:border-brand-300"
                    }`}
                  >
                    {value}
                  </button>
                );
              })}
              <span className="ml-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">Agree</span>
            </div>
          </li>
        ))}
      </ol>

      <button className="tm-btn-primary mt-5" onClick={submit} disabled={!allAnswered || busy}>
        {busy ? "Sending…" : allAnswered ? "Send my answers" : "Answer all 10 to send"}
      </button>
    </div>
  );
}
