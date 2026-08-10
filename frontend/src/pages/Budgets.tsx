import { useState } from "react";
import { api, ApiError } from "../api/client";
import type { Category } from "../api/types";
import { PageHeader } from "../components/PageHeader";
import { EmptyState, ErrorState, Loading, PartialNotice } from "../components/States";
import { formatMinor } from "../lib/money";
import { useFetch } from "../lib/useFetch";

interface BudgetEntry {
  category_id: number;
  category: string;
  target_minor: number | null;
  actual_minor: number;
  over_minor: number;
}

interface Overview {
  period: string;
  entries: BudgetEntry[];
  uncategorized_minor: number;
  totals: { target_minor: number; actual_minor: number };
}

interface Simulation {
  lookback_complete_months: number;
  months_ahead: number;
  adjustments: { category: string; percent_change: number;
    monthly_mean_minor: number; monthly_min_minor: number;
    monthly_max_minor: number; adjusted_mean_minor: number }[];
  monthly_delta_minor: number;
  projection: { month: string; baseline_power_minor: number;
    adjusted_power_minor: number; cumulative_delta_minor: number }[];
  summary: string;
  model_explanation: string | null;
  watch_out_for: string | null;
}

const thisMonth = () => new Date().toISOString().slice(0, 7);

export function Budgets() {
  const [period, setPeriod] = useState(thisMonth());
  const overview = useFetch<Overview>(`/api/budgets/overview?period=${period}`);
  const categories = useFetch<Category[]>("/api/categories");
  const [notice, setNotice] = useState<string | null>(null);

  async function saveTarget(categoryId: number, dollars: string) {
    const trimmed = dollars.trim();
    try {
      if (trimmed === "") {
        await api.delete?.(`/api/budgets/${categoryId}`);
      } else {
        const minor = Math.round(Number(trimmed) * 100);
        if (!Number.isFinite(minor) || minor < 0) {
          setNotice("Targets are plain dollar amounts, like 400 or 82.50.");
          return;
        }
        await api.put(`/api/budgets/${categoryId}`, { target_minor: minor, period });
      }
      setNotice(null);
      overview.reload();
    } catch (err) {
      if (err instanceof ApiError && err.status === 404 && trimmed === "") return;
      setNotice(err instanceof ApiError ? err.message : "That didn't save.");
    }
  }

  return (
    <>
      <PageHeader title="Budgets & Simulator"
        actions={
          <input type="month" value={period} aria-label="Budget month"
            onChange={(e) => setPeriod(e.target.value || thisMonth())}
            className="border border-rule-strong bg-surface px-2 py-1 text-[13px] focus:border-ink" />
        } />

      {notice && <div className="mb-4"><PartialNotice>{notice}</PartialNotice></div>}

      <div className="grid gap-10 lg:grid-cols-2">
        <section aria-labelledby="b-targets">
          <h2 id="b-targets" className="border-b border-rule-strong pb-2 text-[13px] font-medium">
            Targets vs actuals
          </h2>
          {overview.loading ? (
            <Loading label="Reading the month" />
          ) : overview.error ? (
            <ErrorState happened={overview.error} onRetry={overview.reload} />
          ) : overview.data && overview.data.entries.length === 0 ? (
            <EmptyState title="No spending recorded this month"
              body="Targets appear here once transactions are categorized. Run categorization from the Review page first." />
          ) : overview.data && (
            <>
              <table className="w-full">
                <thead>
                  <tr className="border-b border-rule text-left text-[12px] text-ink-muted">
                    <th className="py-2 pr-3 font-medium">Category</th>
                    <th className="py-2 pr-3 text-right font-medium">Spent</th>
                    <th className="py-2 text-right font-medium">Target ($)</th>
                  </tr>
                </thead>
                <tbody>
                  {overview.data.entries.map((e) => (
                    <tr key={e.category_id} className="border-b border-rule">
                      <td className="py-2 pr-3 text-[13px]">{e.category}</td>
                      <td className={`tabular py-2 pr-3 text-right text-[13px] ${
                        e.over_minor > 0 ? "text-attention" : ""}`}>
                        {formatMinor(e.actual_minor)}
                        {e.over_minor > 0 &&
                          <span className="block text-[11px]">
                            {formatMinor(e.over_minor)} over
                          </span>}
                      </td>
                      <td className="py-2 text-right">
                        <input
                          defaultValue={e.target_minor !== null
                            ? (e.target_minor / 100).toFixed(2) : ""}
                          aria-label={`Target for ${e.category}`}
                          placeholder="—" inputMode="decimal"
                          onBlur={(ev) => {
                            const v = ev.target.value;
                            const prev = e.target_minor !== null
                              ? (e.target_minor / 100).toFixed(2) : "";
                            if (v.trim() !== prev) saveTarget(e.category_id, v);
                          }}
                          className="tabular w-24 border border-transparent bg-transparent py-0.5 text-right text-[13px] hover:border-rule-strong focus:border-ink" />
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="border-t border-rule-strong">
                    <td className="py-2 pr-3 text-[13px] font-medium">Total</td>
                    <td className="tabular py-2 pr-3 text-right text-[13px] font-medium">
                      {formatMinor(overview.data.totals.actual_minor)}
                    </td>
                    <td className="tabular py-2 text-right text-[13px] text-ink-muted">
                      {overview.data.totals.target_minor > 0
                        ? formatMinor(overview.data.totals.target_minor) : "—"}
                    </td>
                  </tr>
                </tfoot>
              </table>
              {overview.data.uncategorized_minor > 0 && (
                <p className="mt-2 text-[12px] text-ink-faint">
                  {formatMinor(overview.data.uncategorized_minor)} of this month's
                  spending is uncategorized and counted only in the total.
                </p>
              )}
            </>
          )}
        </section>

        <Simulator categories={categories.data ?? []} />
      </div>
    </>
  );
}

function Simulator({ categories }: { categories: Category[] }) {
  const [categoryId, setCategoryId] = useState("");
  const [percent, setPercent] = useState("-30");
  const [months, setMonths] = useState("6");
  const [result, setResult] = useState<Simulation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      setResult(await api.post<Simulation>("/api/simulate", {
        adjustments: [{ category_id: Number(categoryId),
          percent_change: Number(percent) }],
        months_ahead: Number(months),
      }));
    } catch (err) {
      setResult(null);
      setError(err instanceof ApiError ? err.message : "The server can't be reached.");
    } finally {
      setBusy(false);
    }
  }

  const control = "border border-rule-strong bg-surface px-2 py-1 text-[13px] focus:border-ink";
  return (
    <section aria-labelledby="b-sim">
      <h2 id="b-sim" className="border-b border-rule-strong pb-2 text-[13px] font-medium">
        What-if simulator
      </h2>
      <div className="flex flex-wrap items-center gap-2 pt-3 text-[13px]">
        <span>What if I change</span>
        <select value={categoryId} aria-label="Category to adjust" className={control}
          onChange={(e) => setCategoryId(e.target.value)}>
          <option value="" disabled>category…</option>
          {categories.slice().sort((a, b) => a.name.localeCompare(b.name)).map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
        <span>by</span>
        <input value={percent} aria-label="Percent change" inputMode="numeric"
          onChange={(e) => setPercent(e.target.value)}
          className={`${control} tabular w-16 text-right`} />
        <span>% for</span>
        <input value={months} aria-label="Months ahead" inputMode="numeric"
          onChange={(e) => setMonths(e.target.value)}
          className={`${control} tabular w-12 text-right`} />
        <span>months?</span>
        <button type="button" disabled={busy || !categoryId} onClick={run}
          className="bg-accent px-4 py-1.5 text-[13px] font-medium text-surface disabled:opacity-50">
          {busy ? "Projecting…" : "Project"}
        </button>
      </div>

      {error && <div className="mt-3"><PartialNotice>{error}</PartialNotice></div>}

      {result && (
        <div className="mt-4">
          <p className="text-[13px]">{result.summary}</p>
          <p className="mt-1 text-[12px] text-ink-faint">
            Based on your actual spending across the last{" "}
            {result.lookback_complete_months} complete months
            {result.adjustments[0] &&
              ` (range ${formatMinor(result.adjustments[0].monthly_min_minor)} – ${
                formatMinor(result.adjustments[0].monthly_max_minor)}/month)`}.
          </p>
          <table className="mt-3 w-full">
            <thead>
              <tr className="border-b border-rule-strong text-left text-[12px] text-ink-muted">
                <th className="py-2 pr-3 font-medium">Month</th>
                <th className="py-2 pr-3 text-right font-medium">Baseline power</th>
                <th className="py-2 pr-3 text-right font-medium">With change</th>
                <th className="py-2 text-right font-medium">Saved</th>
              </tr>
            </thead>
            <tbody>
              {result.projection.map((row) => (
                <tr key={row.month} className="border-b border-rule">
                  <td className="tabular py-1.5 pr-3 text-[12px] text-ink-muted">
                    {row.month}
                  </td>
                  <td className="tabular py-1.5 pr-3 text-right text-[13px]">
                    {formatMinor(row.baseline_power_minor)}
                  </td>
                  <td className="tabular py-1.5 pr-3 text-right text-[13px]">
                    {formatMinor(row.adjusted_power_minor)}
                  </td>
                  <td className="tabular py-1.5 text-right text-[13px] text-positive">
                    {formatMinor(row.cumulative_delta_minor)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {result.model_explanation && (
            <div className="mt-3 border-l-2 border-rule pl-3">
              <p className="text-[13px]">{result.model_explanation}</p>
              {result.watch_out_for && (
                <p className="mt-1 text-[13px] text-ink-muted">
                  Watch for: {result.watch_out_for}
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
