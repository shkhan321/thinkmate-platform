import { FormEvent, useEffect, useRef, useState } from "react";
import { api } from "../api";
import { REASONING_STEPS, conditionTitle, coveredReasoning } from "../flow";
import type { PilotSession, PilotTask, Turn } from "../types";
import { Callout, PedagogyTags, ReasoningMap } from "./ui";
import { ArrowLeftIcon, ChatIcon, LightbulbIcon, SendIcon, SparkIcon } from "./icons";

export function ThinkMateChat({
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
  const [input, setInput] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [hint, setHint] = useState("");
  const [hintLoading, setHintLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const exchanges = Math.ceil(turns.length / 2);
  const covered = coveredReasoning(turns.filter((t) => t.role === "tutor").map((t) => t.move_type));
  const currentKey = REASONING_STEPS.find((step) => !covered.has(step.key))?.key ?? null;

  // Resume the saved conversation when reopening this activity.
  useEffect(() => {
    let active = true;
    api
      .sessionState(session.id)
      .then((state) => active && setTurns(state.turns))
      .catch(() => {
        /* a fresh session simply has no turns yet */
      });
    return () => {
      active = false;
    };
  }, [session.id]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [turns, busy]);

  async function sendTurn(event: FormEvent) {
    event.preventDefault();
    if (!input.trim() || busy) return;
    setBusy(true);
    setError("");
    try {
      const response = await api.dialogueTurn(session.id, input);
      setTurns((current) => [...current, response.student_turn, response.tutor_turn]);
      setInput("");
      setHint("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not send your message. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  async function getHint() {
    if (hintLoading) return;
    setHintLoading(true);
    setError("");
    try {
      const response = await api.dialogueHint(session.id);
      setHint(response.hint);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load a suggestion. Please try again.");
    } finally {
      setHintLoading(false);
    }
  }

  return (
    <div className="tm-rise grid gap-4 lg:grid-cols-[320px_1fr]">
      <aside className="tm-card order-2 h-fit p-5 lg:order-1">
        <span className="tm-chip bg-brand-50 text-brand-700">
          <ChatIcon className="h-3.5 w-3.5" /> {conditionTitle("thinkmate")}
        </span>
        <h2 className="mt-3 text-lg font-extrabold text-slate-900">{task.title}</h2>

        {projectTitle ? (
          <div className="mt-3 rounded-2xl border border-brand-100 bg-brand-50/60 p-3">
            <p className="text-xs font-bold uppercase tracking-wide text-brand-600">Your project</p>
            <p className="mt-0.5 text-sm font-semibold text-slate-800">{projectTitle}</p>
            {projectGoal && <p className="mt-0.5 text-xs text-slate-600">{projectGoal}</p>}
          </div>
        ) : (
          <p className="mt-1 text-sm leading-relaxed text-slate-600">{task.scenario}</p>
        )}

        <div className="mt-4 rounded-2xl bg-slate-50 p-4">
          <ReasoningMap covered={covered} currentKey={currentKey} />
        </div>

        <div className="mt-4 rounded-2xl bg-slate-50 p-4">
          <p className="flex items-center gap-2 text-sm font-bold text-slate-800">
            <LightbulbIcon className="h-4 w-4 text-accent-600" /> How to answer
          </p>
          <ul className="mt-2 space-y-1.5 text-sm text-slate-600">
            <li>• Start with your claim or decision.</li>
            <li>• Give the reason or evidence behind it.</li>
            <li>• Answer ThinkMate's question before moving on.</li>
          </ul>
        </div>

        <button
          className="tm-btn-ghost mt-4 w-full"
          type="button"
          onClick={() => void onFinish()}
          disabled={exchanges === 0 || busy}
        >
          Finish &amp; save
        </button>
        <p className="mt-3 text-center text-xs text-slate-400">
          {exchanges === 0
            ? "Send at least one message to begin"
            : `${exchanges} exchange${exchanges === 1 ? "" : "s"} so far`}
        </p>
      </aside>

      <section className="tm-card order-1 flex h-[32rem] flex-col p-0 sm:h-[34rem] lg:order-2">
        <header className="flex items-center justify-between gap-3 border-b border-slate-100 px-4 py-3 sm:px-5">
          <div className="flex items-center gap-3">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-brand-500 to-accent-500 text-white">
              <SparkIcon className="h-5 w-5" />
            </span>
            <div className="leading-tight">
              <p className="font-bold text-slate-900">ThinkMate</p>
              <p className="text-xs text-slate-500">Asks questions — never gives the answer</p>
            </div>
          </div>
          <button type="button" className="tm-btn-ghost !px-3 !py-1.5 text-xs" onClick={onBack}>
            <ArrowLeftIcon className="h-4 w-4" /> Back
          </button>
        </header>

        <div
          ref={scrollRef}
          className="flex-1 space-y-4 overflow-y-auto px-4 py-5 sm:px-5"
          aria-live="polite"
          aria-label="Conversation with ThinkMate"
        >
          {turns.length === 0 && (
            <div className="mx-auto max-w-md rounded-2xl border border-dashed border-brand-200 bg-brand-50/60 p-5 text-center">
              <p className="font-bold text-slate-800">Start with one clear sentence about your project</p>
              <p className="mt-1 text-sm text-slate-600">
                For example: &ldquo;My main decision is &hellip; because &hellip;&rdquo;
              </p>
            </div>
          )}

          {turns.map((turn) => (
            <MessageBubble key={turn.id} turn={turn} />
          ))}

          {busy && (
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <SparkIcon className="h-4 w-4 animate-pulse text-brand-500" />
              ThinkMate is thinking&hellip;
            </div>
          )}
        </div>

        <div className="border-t border-slate-100 p-3 sm:p-4">
          {error && (
            <div className="mb-3">
              <Callout>{error}</Callout>
            </div>
          )}

          {hint && (
            <div className="mb-3 rounded-2xl border border-accent-200 bg-accent-50/70 p-3">
              <p className="flex items-center gap-1.5 text-xs font-bold text-accent-700">
                <LightbulbIcon className="h-3.5 w-3.5" /> Example to get you started — then make it your own
              </p>
              <p className="mt-1 text-sm text-slate-700">{hint}</p>
            </div>
          )}

          {turns.length > 0 && !hint && (
            <button
              type="button"
              onClick={getHint}
              disabled={hintLoading}
              className="mb-2 text-xs font-semibold text-accent-700 hover:text-accent-600 disabled:text-slate-400"
            >
              {hintLoading ? "Thinking of an example…" : "Stuck? See a suggested reply"}
            </button>
          )}

          <form className="flex items-end gap-2" onSubmit={sendTurn}>
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  void sendTurn(event);
                }
              }}
              rows={1}
              placeholder="Type your reasoning…"
              aria-label="Type your reasoning"
              className="tm-input max-h-32 min-h-[3rem] flex-1 resize-none py-3"
            />
            <button
              className="tm-btn-primary h-12 w-12 shrink-0 !px-0"
              disabled={busy || !input.trim()}
              aria-label="Send message"
            >
              <SendIcon className="h-5 w-5" />
            </button>
          </form>
        </div>
      </section>
    </div>
  );
}

function MessageBubble({ turn }: { turn: Turn }) {
  const isTutor = turn.role === "tutor";
  if (isTutor) {
    return (
      <div className="flex gap-2.5">
        <span className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-brand-500 to-accent-500 text-white">
          <SparkIcon className="h-4 w-4" />
        </span>
        <div className="max-w-[85%]">
          <div className="rounded-2xl rounded-tl-md bg-slate-100 px-4 py-3 text-slate-800">
            <p className="whitespace-pre-wrap leading-relaxed">{turn.content}</p>
          </div>
          <PedagogyTags bloom={turn.bloom_level} paulElder={turn.paul_elder_target} />
        </div>
      </div>
    );
  }
  return (
    <div className="flex justify-end">
      <div className="max-w-[85%] rounded-2xl rounded-tr-md bg-brand-600 px-4 py-3 text-white shadow-sm">
        <p className="whitespace-pre-wrap leading-relaxed">{turn.content}</p>
      </div>
    </div>
  );
}
