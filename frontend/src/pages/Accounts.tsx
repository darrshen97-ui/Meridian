import type { Account, BalanceRow, Institution, SyncStatus } from "../api/types";
import { PageHeader } from "../components/PageHeader";
import { EmptyState, ErrorState, Loading } from "../components/States";
import { shortDate, shortDateTime } from "../lib/dates";
import { formatMinor } from "../lib/money";
import { useFetch } from "../lib/useFetch";

const TYPE_LABEL: Record<string, string> = {
  checking: "Checking", savings: "Savings", credit_card: "Credit card",
  loan: "Loan", crypto: "Crypto", payment_app: "Balance", investment: "Investment",
};

export function Accounts() {
  const accounts = useFetch<Account[]>("/api/accounts");
  const institutions = useFetch<Institution[]>("/api/institutions");
  const balances = useFetch<BalanceRow[]>("/api/balances");
  const sync = useFetch<SyncStatus>("/api/sync/status");

  const loading = accounts.loading || institutions.loading || balances.loading;
  const error = accounts.error ?? institutions.error ?? balances.error;

  const balanceByAccount = new Map(
    (balances.data ?? []).map((b) => [b.account_id, b]));

  const last = sync.data?.last_run;
  return (
    <>
      <PageHeader title="Accounts"
        sub={last?.finished_at
          ? `Last sync ${shortDateTime(last.finished_at)}${
              last.status !== "succeeded" ? ` · ${last.status}` : ""}`
          : "Not synced yet"} />

      {loading ? (
        <Loading label="Reading accounts" />
      ) : error ? (
        <ErrorState happened={error} todo="Check the server, then try again."
          onRetry={() => { accounts.reload(); institutions.reload(); balances.reload(); }} />
      ) : (accounts.data ?? []).length === 0 ? (
        <EmptyState title="No accounts yet"
          body="Sync to pull accounts from your provider, or import a statement on the Documents page." />
      ) : (
        <div className="space-y-8">
          {(institutions.data ?? []).map((inst) => {
            const rows = (accounts.data ?? [])
              .filter((a) => a.institution_id === inst.id)
              .sort((a, b) => Number(a.closed_at !== null) - Number(b.closed_at !== null));
            if (rows.length === 0) return null;
            return (
              <section key={inst.id} aria-label={inst.name}>
                <div className="flex items-baseline justify-between border-b border-rule-strong pb-2">
                  <h2 className="text-[15px] font-medium">{inst.name}</h2>
                  <span className="text-[12px] text-ink-faint">{inst.kind.replace("_", " ")}</span>
                </div>
                <table className="w-full">
                  <tbody>
                    {rows.map((a) => {
                      const balance = balanceByAccount.get(a.id);
                      const closed = a.closed_at !== null;
                      return (
                        <tr key={a.id}
                          className={`border-b border-rule ${closed ? "opacity-55" : ""}`}>
                          <td className="py-2.5 pr-3 text-[13px]">
                            {a.display_name}
                            {a.mask && <span className="text-ink-faint"> ··{a.mask}</span>}
                          </td>
                          <td className="py-2.5 pr-3 text-[12px] text-ink-muted">
                            {TYPE_LABEL[a.type] ?? a.type}
                            {closed && a.closed_at &&
                              ` · closed ${shortDate(a.closed_at)}`}
                          </td>
                          <td className="tabular py-2.5 text-right text-[13px]">
                            {balance ? formatMinor(balance.current_minor) : "—"}
                          </td>
                          <td className="w-28 py-2.5 pl-3 text-right text-[11px] text-ink-faint">
                            {balance ? shortDate(balance.as_of) : "no balance yet"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </section>
            );
          })}
        </div>
      )}
    </>
  );
}
