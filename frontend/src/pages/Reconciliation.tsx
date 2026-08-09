import { useState } from "react";
import { api, ApiError } from "../api/client";
import type { Account } from "../api/types";
import { Money } from "../components/Money";
import { PageHeader } from "../components/PageHeader";
import { EmptyState, ErrorState, Loading, PartialNotice } from "../components/States";
import { shortDate } from "../lib/dates";
import { formatMinor } from "../lib/money";
import { useFetch } from "../lib/useFetch";

interface RunSummary {
  run_id: number;
  account_id: number;
  period_start: string;
  period_end: string;
  statement_ending_minor: number | null;
  computed_ending_minor: number | null;
  delta_minor: number | null;
  status: string;
}

interface Period {
  account_id: number;
  period_start: string;
  period_end: string;
  documents: number;
  last_run: RunSummary | null;
}

interface Finding {
  id: number;
  kind: string;
  narrative: string;
  delta_minor: number | null;
  resolved: boolean;
  transaction: { posted_date: string; description: string; amount_minor: number } | null;
}

type RunDetail = RunSummary & { findings: Finding[] };

const KIND_LABEL: Record<string, string> = {
  missing_in_provider: "Missing from live feed",
  missing_in_statement: "Not on any statement",
  amount_mismatch: "Amounts disagree",
  duplicate_suspected: "Possible duplicate",
  date_shift: "Date shift (matched)",
};

export function Reconciliation() {
  const periods = useFetch<Period[]>("/api/reconciliation/periods");
  const accounts = useFetch<Account[]>("/api/accounts");
  const [detail, setDetail] = useState<RunDetail | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const accountById = new Map((accounts.data ?? []).map((a) => [a.id, a]));

  async function act(label: string, fn: () => Promise<void>) {
    setBusy(label);
    setNotice(null);
    try {
      await fn();
    } catch (err) {
      setNotice(err instanceof ApiError ? err.message : "The server can't be reached.");
    } finally {
      setBusy(null);
    }
  }

  const runOne = (p: Period) => act(`${p.account_id}:${p.period_start}`, async () => {
    const result = await api.post<RunDetail>("/api/reconciliation/run", {
      account_id: p.account_id, period_start: p.period_start, period_end: p.period_end,
    });
    setDetail(result);
    periods.reload();
  });

  const openRun = (runId: number) => act(`open:${runId}`, async () => {
    setDetail(await api.get<RunDetail>(`/api/reconciliation/${runId}`));
  });

  const resolveFinding = (findingId: number) => act(`resolve:${findingId}`, async () => {
    await api.post(`/api/reconciliation/findings/${findingId}/resolve`);
    if (detail) setDetail(await api.get<RunDetail>(`/api/reconciliation/${detail.run_id}`));
    periods.reload();
  });

  return (
    <>
      <PageHeader title="Reconciliation"
        sub="Statement ending balances against the live ledger, period by period."
        actions={
          <button type="button" disabled={busy === "all"}
            onClick={() => act("all", async () => {
              const runs = await api.post<RunDetail[]>("/api/reconciliation/run-all");
              const withFindings = runs.filter((r) => r.status !== "clean").length;
              setNotice(`Reconciled ${runs.length} periods — ${withFindings} with findings.`);
              periods.reload();
            })}
            className="border border-rule-strong px-4 py-1.5 text-[13px] font-medium hover:border-ink disabled:opacity-50">
            {busy === "all" ? "Reconciling…" : "Reconcile all periods"}
          </button>
        } />

      {notice && <div className="mb-4"><PartialNotice>{notice}</PartialNotice></div>}

      {periods.loading ? (
        <Loading label="Finding reconcilable periods" />
      ) : periods.error ? (
        <ErrorState happened={periods.error} onRetry={periods.reload} />
      ) : (periods.data ?? []).length === 0 ? (
        <EmptyState title="Nothing to reconcile yet"
          body="Reconciliation compares an imported statement against the live feed. Import a PDF or OFX statement on the Documents page first." />
      ) : (
        <div className="grid gap-8 lg:grid-cols-[1fr_1fr]">
          <div>
            <table className="w-full">
              <thead>
                <tr className="border-b border-rule-strong text-left text-[12px] text-ink-muted">
                  <th className="py-2 pr-3 font-medium">Account</th>
                  <th className="py-2 pr-3 font-medium">Period</th>
                  <th className="py-2 pr-3 font-medium">Status</th>
                  <th className="py-2 text-right font-medium" aria-label="Actions" />
                </tr>
              </thead>
              <tbody>
                {(periods.data ?? []).map((p) => {
                  const account = accountById.get(p.account_id);
                  const key = `${p.account_id}:${p.period_start}`;
                  return (
                    <tr key={key} className="border-b border-rule align-baseline">
                      <td className="max-w-0 truncate py-2 pr-3 text-[13px]">
                        {account ? `${account.display_name}${account.mask ? ` ··${account.mask}` : ""}` : "—"}
                      </td>
                      <td className="tabular whitespace-nowrap py-2 pr-3 text-[12px] text-ink-muted">
                        {shortDate(p.period_start)} – {shortDate(p.period_end)}
                      </td>
                      <td className="whitespace-nowrap py-2 pr-3 text-[12px]">
                        {p.last_run === null ? (
                          <span className="text-ink-faint">not run</span>
                        ) : p.last_run.status === "clean" ? (
                          <span className="text-positive">clean</span>
                        ) : (
                          <button type="button"
                            onClick={() => openRun(p.last_run!.run_id)}
                            className="text-attention underline-offset-2 hover:underline">
                            findings
                          </button>
                        )}
                      </td>
                      <td className="py-2 text-right">
                        <button type="button" disabled={busy === key}
                          onClick={() => runOne(p)}
                          className="border border-rule-strong px-2 py-0.5 text-[12px] hover:border-ink disabled:opacity-50">
                          {busy === key ? "Running…" : p.last_run ? "Re-run" : "Run"}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div>
            {detail === null ? (
              <EmptyState title="Pick a period"
                body="Run a period, or open one with findings, to see the detail here." />
            ) : (
              <section aria-label="Reconciliation detail">
                <div className="border-b border-rule-strong pb-2">
                  <h2 className="text-[15px] font-medium">
                    {accountById.get(detail.account_id)?.display_name}{" "}
                    <span className="tabular text-[12px] text-ink-muted">
                      {shortDate(detail.period_start)} – {shortDate(detail.period_end)}
                    </span>
                  </h2>
                </div>
                <dl className="text-[13px]">
                  <div className="flex justify-between border-b border-rule py-2">
                    <dt className="text-ink-muted">Statement ending balance</dt>
                    <dd className="tabular">
                      {detail.statement_ending_minor !== null
                        ? formatMinor(detail.statement_ending_minor) : "—"}
                    </dd>
                  </div>
                  <div className="flex justify-between border-b border-rule py-2">
                    <dt className="text-ink-muted">Computed from live ledger</dt>
                    <dd className="tabular">
                      {detail.computed_ending_minor !== null
                        ? formatMinor(detail.computed_ending_minor) : "—"}
                    </dd>
                  </div>
                  <div className="flex justify-between border-b border-rule py-2">
                    <dt className="text-ink-muted">Difference</dt>
                    <dd className={`tabular ${detail.delta_minor ? "text-attention" : ""}`}>
                      {detail.delta_minor !== null ? formatMinor(detail.delta_minor) : "—"}
                    </dd>
                  </div>
                </dl>

                {detail.findings.length === 0 ? (
                  <p className="py-4 text-[13px] text-positive">
                    Clean — every transaction matched across both sources.
                  </p>
                ) : (
                  <ul className="mt-3 space-y-3">
                    {detail.findings.map((f) => (
                      <li key={f.id}
                        className={`border-l-2 pl-3 ${
                          f.resolved ? "border-rule opacity-60" : "border-attention"}`}>
                        <p className="text-[11px] uppercase tracking-wide text-ink-faint">
                          {KIND_LABEL[f.kind] ?? f.kind}
                          {f.resolved && " · resolved"}
                        </p>
                        <p className="mt-0.5 text-[13px]">{f.narrative}</p>
                        {f.transaction && (
                          <p className="tabular mt-0.5 text-[12px] text-ink-muted">
                            {shortDate(f.transaction.posted_date)} ·{" "}
                            <Money minor={f.transaction.amount_minor} className="text-[12px]" />
                          </p>
                        )}
                        {!f.resolved && (
                          <button type="button" disabled={busy === `resolve:${f.id}`}
                            onClick={() => resolveFinding(f.id)}
                            className="mt-1 border border-rule-strong px-2 py-0.5 text-[12px] hover:border-ink disabled:opacity-50">
                            Resolve
                          </button>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            )}
          </div>
        </div>
      )}
    </>
  );
}
