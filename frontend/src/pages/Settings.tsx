import { useState } from "react";
import { api, ApiError } from "../api/client";
import type { SyncStatus } from "../api/types";
import { useAuth } from "../auth";
import { PageHeader } from "../components/PageHeader";
import { ErrorState, Loading, PartialNotice } from "../components/States";
import { shortDateTime } from "../lib/dates";
import { setThemePreference, themePreference } from "../theme";
import { useFetch } from "../lib/useFetch";
import { ModelUnavailable } from "./Review";

interface AiStatus {
  provider: string;
  endpoint: string;
  endpoint_is_local: boolean;
  model: string;
  reachable: boolean;
  model_present: boolean;
  models: string[];
  sends_data_off_device: boolean;
  last_call: { feature: string; status: string; latency_ms: number | null;
    at: string | null } | null;
  totals: { calls: number; input_tokens: number; output_tokens: number;
    avg_latency_ms: number | null };
  enable_hint: string | null;
}

interface AuditRow {
  id: number;
  event: string;
  detail: Record<string, unknown> | null;
  created_at: string;
}

const MODELS = [
  { id: "qwen2.5:7b-instruct",
    hint: "Default. Best quality; needs ~8 GB of memory, comfortable on any modest GPU." },
  { id: "qwen2.5:3b-instruct",
    hint: "Smaller and faster on plain CPUs; sends a few more transactions to review." },
];

const sectionTitle = "border-b border-rule-strong pb-2 text-[13px] font-medium";
const btn = "border border-rule-strong px-3 py-1 text-[13px] font-medium hover:border-ink disabled:opacity-50";

export function Settings() {
  const { me } = useAuth();
  const ai = useFetch<AiStatus>("/api/ai/status");
  const sync = useFetch<SyncStatus>("/api/sync/status");
  const audit = useFetch<AuditRow[]>("/api/audit?limit=50");
  const [theme, setTheme] = useState(themePreference());
  const [notice, setNotice] = useState<string | null>(null);
  const [selftest, setSelftest] = useState<{ latency_ms: number;
    recommendation: string } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  async function act(label: string, fn: () => Promise<void>) {
    setBusy(label);
    setNotice(null);
    try {
      await fn();
    } catch (err) {
      setNotice(err instanceof ApiError ? err.message : "That didn't work — server unreachable.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <PageHeader title="Settings" />
      {notice && <div className="mb-4"><PartialNotice>{notice}</PartialNotice></div>}

      <div className="max-w-2xl space-y-10">
        <section aria-labelledby="s-profile">
          <h2 id="s-profile" className={sectionTitle}>Profile</h2>
          <dl className="pt-2 text-[13px]">
            <div className="flex justify-between border-b border-rule py-2">
              <dt className="text-ink-muted">Name</dt><dd>{me?.display_name}</dd>
            </div>
            <div className="flex justify-between border-b border-rule py-2">
              <dt className="text-ink-muted">Email</dt><dd>{me?.email}</dd>
            </div>
          </dl>
        </section>

        <section aria-labelledby="s-appearance">
          <h2 id="s-appearance" className={sectionTitle}>Appearance</h2>
          <div className="flex gap-2 pt-3">
            {(["system", "light", "dark"] as const).map((pref) => (
              <button key={pref} type="button"
                onClick={() => { setThemePreference(pref); setTheme(pref); }}
                className={`border px-3 py-1 text-[13px] ${
                  theme === pref ? "border-accent text-ink" : "border-rule-strong text-ink-muted"}`}>
                {pref === "system" ? "Follow system" : pref === "light" ? "Light" : "Dark"}
              </button>
            ))}
          </div>
        </section>

        <section aria-labelledby="s-ai">
          <h2 id="s-ai" className={sectionTitle}>AI — local model</h2>
          {ai.loading ? <Loading label="Checking the model" /> :
           ai.error ? <ErrorState happened={ai.error} onRetry={ai.reload} /> :
           ai.data && (
            <div className="pt-2 text-[13px]">
              <dl>
                <div className="flex justify-between border-b border-rule py-2">
                  <dt className="text-ink-muted">Endpoint</dt>
                  <dd className="tabular text-[12px]">
                    {ai.data.endpoint}
                    <span className={ai.data.endpoint_is_local
                      ? "ml-2 text-positive" : "ml-2 text-critical"}>
                      {ai.data.endpoint_is_local ? "local" : "NOT LOCAL — AI disabled"}
                    </span>
                  </dd>
                </div>
                <div className="flex justify-between border-b border-rule py-2">
                  <dt className="text-ink-muted">Ollama</dt>
                  <dd>{ai.data.reachable ? "running" : "not running"}</dd>
                </div>
                <div className="flex justify-between border-b border-rule py-2">
                  <dt className="text-ink-muted">Model</dt>
                  <dd>{ai.data.model} — {ai.data.model_present ? "installed" : "not pulled"}</dd>
                </div>
                {ai.data.last_call && (
                  <div className="flex justify-between border-b border-rule py-2">
                    <dt className="text-ink-muted">Last call</dt>
                    <dd className="tabular text-[12px]">
                      {ai.data.last_call.feature} · {ai.data.last_call.status} ·{" "}
                      {ai.data.last_call.latency_ms ?? "—"} ms
                    </dd>
                  </div>
                )}
              </dl>

              {ai.data.sends_data_off_device && (
                <p className="mt-2 border-l-2 border-critical pl-3 text-[13px] text-critical">
                  The active provider sends transaction data off this machine. The
                  product default is the local model; switch LLM_PROVIDER back to
                  ollama unless you chose this deliberately.
                </p>
              )}
              {!ai.data.model_present && ai.data.endpoint_is_local && (
                <ModelUnavailable message={ai.data.enable_hint} />
              )}

              <div className="mt-4 space-y-2">
                <p className="text-[12px] uppercase tracking-wide text-ink-faint">Model choice</p>
                {MODELS.map((m) => (
                  <label key={m.id} className="flex items-baseline gap-2">
                    <input type="radio" name="model" checked={ai.data!.model === m.id}
                      onChange={() => act("model", async () => {
                        await api.put("/api/ai/model", { model: m.id });
                        ai.reload();
                      })} />
                    <span>
                      <span className="tabular text-[13px]">{m.id}</span>
                      <span className="block text-[12px] text-ink-muted">{m.hint}</span>
                    </span>
                  </label>
                ))}
                <button type="button" disabled={busy === "selftest" || !ai.data.model_present}
                  onClick={() => act("selftest", async () => {
                    setSelftest(await api.post("/api/ai/selftest"));
                  })}
                  className={btn}>
                  {busy === "selftest" ? "Testing…" : "Run speed test"}
                </button>
                {selftest && (
                  <p className="text-[13px] text-ink-muted">
                    {(selftest.latency_ms / 1000).toFixed(1)}s for one batch. {selftest.recommendation}
                  </p>
                )}
              </div>

              <div className="mt-5">
                <p className="text-[12px] uppercase tracking-wide text-ink-faint">Usage</p>
                <table className="mt-1 w-full text-[13px]">
                  <tbody>
                    <tr className="border-b border-rule">
                      <td className="py-1.5 text-ink-muted">Model calls</td>
                      <td className="tabular text-right">{ai.data.totals.calls.toLocaleString()}</td>
                    </tr>
                    <tr className="border-b border-rule">
                      <td className="py-1.5 text-ink-muted">Tokens in / out</td>
                      <td className="tabular text-right">
                        {ai.data.totals.input_tokens.toLocaleString()} /{" "}
                        {ai.data.totals.output_tokens.toLocaleString()}
                      </td>
                    </tr>
                    <tr className="border-b border-rule">
                      <td className="py-1.5 text-ink-muted">Average latency</td>
                      <td className="tabular text-right">
                        {ai.data.totals.avg_latency_ms !== null
                          ? `${ai.data.totals.avg_latency_ms.toLocaleString()} ms` : "—"}
                      </td>
                    </tr>
                    <tr className="border-b border-rule">
                      <td className="py-1.5 text-ink-muted">Cost</td>
                      <td className="tabular text-right">$0.00 — the model runs on this machine</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </section>

        <section aria-labelledby="s-sync">
          <h2 id="s-sync" className={sectionTitle}>Sync</h2>
          <div className="pt-2 text-[13px]">
            <p className="text-ink-muted">
              {sync.data?.last_run
                ? `Last sync ${sync.data.last_run.finished_at
                    ? shortDateTime(sync.data.last_run.finished_at) : "in progress"} · ${
                    sync.data.last_run.status}`
                : "Not synced yet."}
            </p>
            <div className="mt-2 flex gap-2">
              <button type="button" disabled={busy === "sync"} className={btn}
                onClick={() => act("sync", async () => {
                  await api.post("/api/sync");
                  sync.reload();
                  setNotice("Synced.");
                })}>
                {busy === "sync" ? "Syncing…" : "Sync now"}
              </button>
            </div>

            <div className="mt-5 border-l-2 border-attention pl-3">
              <p className="text-[12px] font-medium uppercase tracking-wide text-attention">
                Development tool
              </p>
              <p className="mt-1 text-[13px] text-ink-muted">
                Injects a few plausible transactions into the mock provider feed, then
                syncs — for watching the live path work on demand. Not part of normal use.
              </p>
              <button type="button" disabled={busy === "simulate"} className={`mt-2 ${btn}`}
                onClick={() => act("simulate", async () => {
                  const r = await api.post<{ injected: number }>(
                    "/api/dev/simulate-transactions", { count: 3 });
                  setNotice(`Injected ${r.injected} simulated transactions and synced.`);
                  sync.reload();
                })}>
                {busy === "simulate" ? "Working…" : "Simulate incoming transactions"}
              </button>
            </div>
          </div>
        </section>

        <section aria-labelledby="s-audit">
          <h2 id="s-audit" className={sectionTitle}>Audit log</h2>
          {audit.loading ? <Loading label="Reading the log" /> :
           audit.error ? <ErrorState happened={audit.error} onRetry={audit.reload} /> :
           (audit.data ?? []).length === 0 ? (
            <p className="pt-2 text-[13px] text-ink-muted">Nothing logged yet.</p>
          ) : (
            <table className="mt-1 w-full text-[12px]">
              <tbody>
                {(audit.data ?? []).map((row) => (
                  <tr key={row.id} className="border-b border-rule align-baseline">
                    <td className="tabular whitespace-nowrap py-1.5 pr-3 text-ink-faint">
                      {shortDateTime(row.created_at)}
                    </td>
                    <td className="whitespace-nowrap py-1.5 pr-3">{row.event}</td>
                    <td className="tabular max-w-0 truncate py-1.5 text-ink-muted">
                      {row.detail ? JSON.stringify(row.detail) : ""}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </div>
    </>
  );
}
