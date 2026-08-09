import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { SyncStatus, Transaction } from "../api/types";
import { Money } from "../components/Money";
import { PageHeader } from "../components/PageHeader";
import { EmptyState, ErrorState, Loading } from "../components/States";
import { shortDate, shortDateTime } from "../lib/dates";
import { formatMinor } from "../lib/money";
import { useEvents } from "../lib/useEvents";
import { useFetch } from "../lib/useFetch";

interface Overview {
  as_of: string;
  spending_power_minor: number;
  liquid_minor: number;
  obligations_minor: number;
  liquid_accounts: { account_id: number; display_name: string; mask: string | null;
    current_minor: number | null; as_of: string | null }[];
  card_balances: { account_id: number; display_name: string; mask: string | null;
    owed_minor: number }[];
  this_month: { label: string; spent_minor: number; income_minor: number };
  last_month: { label: string; spent_minor: number; income_minor: number };
  needs_attention: { review_count: number; unresolved_findings: number };
  recent: Transaction[];
}

export function Dashboard() {
  const overview = useFetch<Overview>("/api/dashboard");
  const syncStatus = useFetch<SyncStatus>("/api/sync/status");
  const [syncing, setSyncing] = useState(false);
  const [syncNote, setSyncNote] = useState<string | null>(null);

  useEvents({
    "sync.started": () => { setSyncing(true); setSyncNote("Syncing…"); },
    "sync.account_done": (data) => {
      const d = data as { display_name: string; status: string };
      setSyncNote(`Syncing — ${d.display_name} ${d.status === "ok" ? "done" : "failed"}`);
    },
    "sync.completed": (data) => {
      const d = data as { new_transactions: number };
      setSyncing(false);
      setSyncNote(d.new_transactions > 0
        ? `Synced — ${d.new_transactions} new transaction${d.new_transactions === 1 ? "" : "s"}`
        : "Synced — nothing new");
      overview.reload();
      syncStatus.reload();
    },
    "sync.failed": () => { setSyncing(false); setSyncNote("Sync failed"); syncStatus.reload(); },
    "transactions.new": () => overview.reload(),
  });

  async function syncNow() {
    setSyncing(true);
    setSyncNote("Syncing…");
    try {
      await api.post("/api/sync");
    } catch (err) {
      setSyncing(false);
      setSyncNote(err instanceof Error ? err.message : "Sync failed");
    }
  }

  const last = syncStatus.data?.last_run;
  return (
    <>
      <PageHeader
        title="Dashboard"
        sub={overview.data ? `As of ${shortDate(overview.data.as_of)}` : undefined}
        actions={
          <div className="text-right">
            <button type="button" onClick={syncNow} disabled={syncing}
              className="border border-rule-strong px-4 py-1.5 text-[13px] font-medium hover:border-ink disabled:opacity-50">
              {syncing ? "Syncing…" : "Sync now"}
            </button>
            <p className="mt-1 text-[12px] text-ink-faint" role="status">
              {syncNote ?? (last
                ? last.status === "failed"
                  ? `Last sync failed — ${last.error ?? "unknown error"}`
                  : `Last sync ${last.finished_at ? shortDateTime(last.finished_at) : "—"}`
                : "Not synced yet")}
            </p>
          </div>
        }
      />

      {overview.loading ? (
        <Loading label="Reading your accounts" />
      ) : overview.error ? (
        <ErrorState happened={overview.error}
          todo="Check that the server is running, then try again."
          onRetry={overview.reload} />
      ) : overview.data && (
        <div className="space-y-10">
          <section aria-labelledby="sp">
            <h2 id="sp" className="text-[13px] text-ink-muted">Spending power</h2>
            <p className="tabular mt-1 text-[32px] font-medium leading-none">
              {formatMinor(overview.data.spending_power_minor)}
            </p>
            <p className="mt-2 text-[13px] text-ink-muted">
              {formatMinor(overview.data.liquid_minor)} liquid −{" "}
              {formatMinor(overview.data.obligations_minor)} card balances due.
              Investments and crypto are not counted.
            </p>
          </section>

          <section className="grid gap-10 md:grid-cols-2">
            <div>
              <h2 className="border-b border-rule-strong pb-2 text-[13px] font-medium">
                {overview.data.this_month.label} vs {overview.data.last_month.label}
              </h2>
              <table className="w-full">
                <tbody>
                  <Row label="Spent"
                    a={-overview.data.this_month.spent_minor}
                    b={-overview.data.last_month.spent_minor} />
                  <Row label="Income"
                    a={overview.data.this_month.income_minor}
                    b={overview.data.last_month.income_minor} />
                </tbody>
              </table>
              <p className="mt-1 text-[12px] text-ink-faint">
                This month · last month. Transfers between your own accounts aren't counted.
              </p>
            </div>

            <div>
              <h2 className="border-b border-rule-strong pb-2 text-[13px] font-medium">
                Needs attention
              </h2>
              <ul>
                <li className="flex items-baseline justify-between border-b border-rule py-2">
                  <Link to="/review" className="text-[15px] underline-offset-2 hover:underline">
                    Transactions to review
                  </Link>
                  <span className={`tabular text-[15px] ${
                    overview.data.needs_attention.review_count > 0 ? "text-attention" : ""}`}>
                    {overview.data.needs_attention.review_count.toLocaleString()}
                  </span>
                </li>
                <li className="flex items-baseline justify-between border-b border-rule py-2">
                  <Link to="/reconciliation"
                    className="text-[15px] underline-offset-2 hover:underline">
                    Reconciliation findings
                  </Link>
                  <span className="tabular text-[15px]">
                    {overview.data.needs_attention.unresolved_findings}
                  </span>
                </li>
              </ul>
            </div>
          </section>

          <section className="grid gap-10 md:grid-cols-2">
            <div>
              <h2 className="border-b border-rule-strong pb-2 text-[13px] font-medium">
                Liquid accounts
              </h2>
              {overview.data.liquid_accounts.length === 0 ? (
                <EmptyState title="No liquid accounts yet"
                  body="Sync your accounts or import a statement to get started." />
              ) : (
                <table className="w-full">
                  <tbody>
                    {overview.data.liquid_accounts.map((a) => (
                      <tr key={a.account_id} className="border-b border-rule">
                        <td className="py-2 text-[13px]">
                          {a.display_name}
                          {a.mask && <span className="text-ink-faint"> ··{a.mask}</span>}
                        </td>
                        <td className="tabular py-2 text-right text-[13px]">
                          {a.current_minor === null ? "—" : formatMinor(a.current_minor)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
            <div>
              <h2 className="border-b border-rule-strong pb-2 text-[13px] font-medium">
                Card balances due
              </h2>
              {overview.data.card_balances.length === 0 ? (
                <p className="py-3 text-[13px] text-ink-muted">Nothing owed on cards.</p>
              ) : (
                <table className="w-full">
                  <tbody>
                    {overview.data.card_balances.map((c) => (
                      <tr key={c.account_id} className="border-b border-rule">
                        <td className="py-2 text-[13px]">
                          {c.display_name}
                          {c.mask && <span className="text-ink-faint"> ··{c.mask}</span>}
                        </td>
                        <td className="tabular py-2 text-right text-[13px]">
                          {formatMinor(c.owed_minor)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </section>

          <section>
            <div className="flex items-baseline justify-between border-b border-rule-strong pb-2">
              <h2 className="text-[13px] font-medium">Recent activity</h2>
              <Link to="/transactions"
                className="text-[12px] text-ink-muted underline-offset-2 hover:underline">
                All transactions
              </Link>
            </div>
            {overview.data.recent.length === 0 ? (
              <EmptyState title="No activity yet"
                body="Sync your accounts or import a statement — the ledger fills from there." />
            ) : (
              <table className="w-full">
                <tbody>
                  {overview.data.recent.map((t) => (
                    <tr key={t.id} className="border-b border-rule">
                      <td className="tabular w-24 py-2 pr-3 text-[12px] text-ink-faint">
                        {shortDate(t.posted_date)}
                      </td>
                      <td className="max-w-0 truncate py-2 pr-3 text-[13px]">
                        {t.description_raw}
                      </td>
                      <td className="py-2 text-right">
                        <Money minor={t.amount_minor} className="text-[13px]" />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </div>
      )}
    </>
  );
}

function Row({ label, a, b }: { label: string; a: number; b: number }) {
  return (
    <tr className="border-b border-rule">
      <td className="py-2 text-[13px]">{label}</td>
      <td className="tabular py-2 text-right text-[13px]">{formatMinor(a)}</td>
      <td className="tabular py-2 pl-4 text-right text-[13px] text-ink-faint">
        {formatMinor(b)}
      </td>
    </tr>
  );
}
