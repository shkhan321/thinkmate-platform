import { FormEvent, useEffect, useState } from "react";
import { courseLabel, firstName, projectDraftKey, projectExamples } from "../flow";
import type { Student } from "../types";
import { Callout } from "./ui";
import { ArrowRightIcon, SparkIcon } from "./icons";

export function ProjectIntake({
  student,
  onSave,
  error,
  pending
}: {
  student: Student | null;
  onSave: (title: string, goal: string) => void;
  error: string;
  pending: boolean;
}) {
  const draftKey = projectDraftKey(student?.student_id);

  function readDraft(): { title: string; goal: string } | null {
    if (!draftKey) return null;
    try {
      const raw = window.localStorage.getItem(draftKey);
      return raw ? (JSON.parse(raw) as { title: string; goal: string }) : null;
    } catch {
      return null;
    }
  }

  const draft = readDraft();
  const [title, setTitle] = useState(draft?.title ?? student?.project_title ?? "");
  const [goal, setGoal] = useState(draft?.goal ?? student?.project_goal ?? "");
  const ready = title.trim().length > 0 && goal.trim().length > 0;
  const examples = projectExamples(student?.course ?? "engineering");

  // Keep a local draft so a refresh before "Start thinking" never loses typing.
  useEffect(() => {
    if (!draftKey) return;
    try {
      if (title.trim() || goal.trim()) {
        window.localStorage.setItem(draftKey, JSON.stringify({ title, goal }));
      } else {
        window.localStorage.removeItem(draftKey);
      }
    } catch {
      /* private mode: drafts just won't persist */
    }
  }, [draftKey, title, goal]);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (ready) onSave(title, goal);
  }

  return (
    <section className="tm-card tm-rise mx-auto max-w-2xl p-6 sm:p-8">
      <div className="flex items-center gap-3">
        <span className="grid h-11 w-11 place-items-center rounded-2xl bg-gradient-to-br from-brand-500 to-accent-500 text-white">
          <SparkIcon className="h-6 w-6" />
        </span>
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-brand-600">Tell ThinkMate about your work</p>
          <h2 className="text-xl font-extrabold text-slate-900">
            Hi {firstName(student?.display_name)} — what are you working on?
          </h2>
        </div>
      </div>

      <p className="mt-3 text-slate-600">
        ThinkMate works on <strong>your own</strong> {student ? courseLabel(student.course) : ""} capstone — whatever
        the topic. Tell it your project so every question is about your real work, not a made-up example.
      </p>

      {error && (
        <div className="mt-4">
          <Callout>{error}</Callout>
        </div>
      )}

      <form className="mt-5 space-y-5" onSubmit={submit}>
        <div>
          <label htmlFor="project-title" className="block text-sm font-semibold text-slate-700">
            What is your project?
          </label>
          <input
            id="project-title"
            className="tm-input mt-1.5"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder={examples.title}
            maxLength={200}
          />
        </div>

        <div>
          <label htmlFor="project-goal" className="block text-sm font-semibold text-slate-700">
            What are you trying to do or decide?
          </label>
          <textarea
            id="project-goal"
            className="tm-input mt-1.5 min-h-[5rem] resize-y"
            value={goal}
            onChange={(event) => setGoal(event.target.value)}
            placeholder={examples.goal}
            maxLength={2000}
          />
          <p className="mt-1.5 text-xs text-slate-400">
            One or two lines is plenty. You can be rough — ThinkMate will ask to sharpen it.
          </p>
        </div>

        <button className="tm-btn-primary w-full sm:w-auto" disabled={!ready || pending}>
          {pending ? "Setting up…" : <>Start thinking <ArrowRightIcon className="h-5 w-5" /></>}
        </button>
      </form>
    </section>
  );
}
