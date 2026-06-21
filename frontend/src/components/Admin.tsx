import { useState } from "react";
import { api } from "../api";
import type { AdminSummary } from "../types";
import { Callout } from "./ui";

export function AdminPanel() {
  const [password, setPassword] = useState("");
  const [authed, setAuthed] = useState(false);
  const [summary, setSummary] = useState<AdminSummary | null>(null);
  const [exportText, setExportText] = useState("");
  const [blinded, setBlinded] = useState(true);
  const [error, setError] = useState("");

  async function loadSummary() {
    setError("");
    try {
      const result = await api.adminSummary(password);
      setSummary(result);
      setAuthed(true);
    } catch (err) {
      setAuthed(false);
      setSummary(null);
      setError(err instanceof Error ? err.message : "Admin request failed.");
    }
  }

  async function exportData(format: "json" | "csv") {
    setError("");
    try {
      if (format === "json") {
        const data = await api.adminExportJson(password, blinded);
        setExportText(JSON.stringify(data, null, 2));
      } else {
        setExportText(await api.adminExportCsv(password, blinded));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed.");
    }
  }

  const stats = summary
    ? [
        { label: "Students", value: summary.students },
        { label: "Sessions", value: summary.sessions },
        { label: "Chat turns", value: summary.turns },
        { label: "Worksheet rows", value: summary.worksheet_responses }
      ]
    : [];

  return (
    <section className="tm-rise mx-auto max-w-4xl space-y-5">
      <div className="tm-card p-6">
        <p className="text-xs font-bold uppercase tracking-wide text-brand-600">Research team only</p>
        <h1 className="mt-1 text-2xl font-extrabold text-slate-900">Pilot monitoring &amp; export</h1>
        <p className="mt-1 text-sm text-slate-600">
          View live pilot counts and export data for analysis or blinded rubric scoring. Do not share the admin
          password with students.
        </p>

        {error && (
          <div className="mt-4">
            <Callout>{error}</Callout>
          </div>
        )}

        <div className="mt-5 grid gap-3 sm:grid-cols-[1fr_auto]">
          <input
            type="password"
            value={password}
            onChange={(event) => {
              setPassword(event.target.value);
              setAuthed(false);
            }}
            placeholder="Admin password"
            className="tm-input"
          />
          <label className="flex items-center gap-2 rounded-2xl bg-slate-50 px-4 text-sm font-semibold text-slate-700">
            <input
              type="checkbox"
              checked={blinded}
              onChange={(event) => setBlinded(event.target.checked)}
              className="h-4 w-4 accent-brand-600"
            />
            Blinded export
          </label>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button className="tm-btn-primary" onClick={loadSummary} disabled={!password}>
            {authed ? "Refresh summary" : "Load summary"}
          </button>
          <button className="tm-btn-ghost" onClick={() => exportData("json")} disabled={!authed}>
            Export JSON
          </button>
          <button className="tm-btn-ghost" onClick={() => exportData("csv")} disabled={!authed}>
            Export CSV
          </button>
          {!authed && (
            <span className="text-xs text-slate-400">Load the summary first to unlock exports.</span>
          )}
        </div>
      </div>

      {summary && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {stats.map((stat) => (
            <div key={stat.label} className="tm-card p-5 text-center">
              <p className="text-3xl font-extrabold text-brand-700">{stat.value}</p>
              <p className="mt-1 text-xs font-semibold uppercase tracking-wide text-slate-500">{stat.label}</p>
            </div>
          ))}
        </div>
      )}

      {exportText && (
        <div className="tm-card p-4">
          <textarea
            className="h-80 w-full resize-y rounded-2xl border border-slate-200 bg-slate-900 p-4 font-mono text-xs text-slate-100"
            value={exportText}
            readOnly
          />
        </div>
      )}
    </section>
  );
}
