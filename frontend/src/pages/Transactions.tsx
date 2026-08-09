import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, ApiError } from "../api/client";
import type { Account, Category, Transaction } from "../api/types";
import { Money } from "../components/Money";
import { PageHeader } from "../components/PageHeader";
import { EmptyState, ErrorState, Loading, PartialNotice } from "../components/States";
import { shortDate } from "../lib/dates";
import { useEvents } from "../lib/useEvents";
import { useFetch } from "../lib/useFetch";

const PAGE = 100;

interface Filters {
  q: string;
  account_id: string;
  source: string;
  date_from: string;
  date_to: string;
  uncategorized: boolean;
}

const EMPTY_FILTERS: Filters = {
  q: "", account_id: "", source: "", date_from: "", date_to: "", uncategorized: false,
};

function query(filters: Filters, offset: number): string {
  const params = new URLSearchParams();
  if (filters.q) params.set("q", filters.q);
  if (filters.account_id) params.set("account_id", filters.account_id);
  if (filters.source) params.set("source", filters.source);
  if (filters.date_from) params.set("date_from", filters.date_from);
  if (filters.date_to) params.set("date_to", filters.date_to);
  if (filters.uncategorized) params.set("uncategorized", "true");
  params.set("limit", String(PAGE));
  params.set("offset", String(offset));
  return `/api/transactions?${params.toString()}`;
}

export function sourceLabel(t: Transaction): string {
  const fromDoc = t.source_document_id !== null;
  const fromProvider = t.external_id !== null;
  if (fromDoc && fromProvider) return "both";
  if (fromDoc) return "statement";
  if (fromProvider) return "live";
  return t.source;
}

export function Transactions() {
  const accounts = useFetch<Account[]>("/api/accounts");
  const categories = useFetch<Category[]>("/api/categories");
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const [debouncedQ, setDebouncedQ] = useState("");
  const [rows, setRows] = useState<Transaction[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [patchError, setPatchError] = useState<string | null>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(filters.q), 250);
    return () => clearTimeout(t);
  }, [filters.q]);

  const effective = useMemo(() => ({ ...filters, q: debouncedQ }),
    [filters, debouncedQ]);

  const load = useCallback(async (offset: number, append: boolean) => {
    try {
      const page = await api.get<Transaction[]>(query(effective, offset));
      setRows((prev) => (append && prev ? [...prev, ...page] : page));
      setHasMore(page.length === PAGE);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The server can't be reached.");
    }
  }, [effective]);

  useEffect(() => {
    setRows(null);
    load(0, false);
  }, [load]);

  useEvents({ "transactions.new": () => load(0, false) });

  async function setCategory(t: Transaction, categoryId: number) {
    const previous = rows;
    setRows((r) => r?.map((x) =>
      x.id === t.id ? { ...x, category_id: categoryId, category_source: "user" } : x) ?? null);
    try {
      await api.patch(`/api/transactions/${t.id}/category`, { category_id: categoryId });
    } catch (err) {
      setRows(previous ?? null);
      setPatchError(err instanceof ApiError ? err.message : "The change didn't save.");
      return;
    }
    setPatchError(null);
  }

  const accountById = new Map((accounts.data ?? []).map((a) => [a.id, a]));
  const sortedCategories = (categories.data ?? [])
    .slice().sort((a, b) => a.name.localeCompare(b.name));

  const control =
    "border border-rule-strong bg-surface px-2 py-1 text-[13px] focus:border-ink";

  return (
    <>
      <PageHeader title="Transactions"
        sub="The ledger — filter, search, and correct categories inline." />

      <div className="flex flex-wrap items-center gap-2 border-b border-rule pb-3">
        <input ref={searchRef} type="search" placeholder="Search descriptions"
          aria-label="Search descriptions" value={filters.q} className={`${control} w-56`}
          onChange={(e) => setFilters((f) => ({ ...f, q: e.target.value }))} />
        <select aria-label="Account" value={filters.account_id} className={control}
          onChange={(e) => setFilters((f) => ({ ...f, account_id: e.target.value }))}>
          <option value="">All accounts</option>
          {(accounts.data ?? []).map((a) => (
            <option key={a.id} value={a.id}>
              {a.display_name}{a.mask ? ` ··${a.mask}` : ""}
            </option>
          ))}
        </select>
        <select aria-label="Source" value={filters.source} className={control}
          onChange={(e) => setFilters((f) => ({ ...f, source: e.target.value }))}>
          <option value="">Any source</option>
          <option value="statement">Statement</option>
          <option value="provider">Live</option>
          <option value="both">Both</option>
        </select>
        <input type="date" aria-label="From date" value={filters.date_from}
          className={control}
          onChange={(e) => setFilters((f) => ({ ...f, date_from: e.target.value }))} />
        <input type="date" aria-label="To date" value={filters.date_to} className={control}
          onChange={(e) => setFilters((f) => ({ ...f, date_to: e.target.value }))} />
        <label className="flex items-center gap-1.5 text-[13px] text-ink-muted">
          <input type="checkbox" checked={filters.uncategorized}
            onChange={(e) =>
              setFilters((f) => ({ ...f, uncategorized: e.target.checked }))} />
          Uncategorized only
        </label>
        {(filters.q || filters.account_id || filters.source || filters.date_from ||
          filters.date_to || filters.uncategorized) && (
          <button type="button" onClick={() => setFilters(EMPTY_FILTERS)}
            className="text-[13px] text-ink-muted underline-offset-2 hover:underline">
            Clear filters
          </button>
        )}
      </div>

      {patchError && <div className="mt-3"><PartialNotice>{patchError}</PartialNotice></div>}

      {rows === null && !error ? (
        <Loading label="Reading the ledger" />
      ) : error ? (
        <ErrorState happened={error} todo="Check the server, then try again."
          onRetry={() => load(0, false)} />
      ) : rows !== null && rows.length === 0 ? (
        <EmptyState title="No transactions match"
          body="Loosen the filters, sync your accounts, or import a statement." />
      ) : rows !== null && (
        <>
          <table className="mt-1 w-full">
            <thead>
              <tr className="border-b border-rule-strong text-left text-[12px] text-ink-muted">
                <th className="py-2 pr-3 font-medium">Date</th>
                <th className="py-2 pr-3 font-medium">Description</th>
                <th className="hidden py-2 pr-3 font-medium md:table-cell">Account</th>
                <th className="hidden py-2 pr-3 font-medium sm:table-cell">Source</th>
                <th className="py-2 pr-3 font-medium">Category</th>
                <th className="py-2 text-right font-medium">Amount</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((t) => {
                const account = accountById.get(t.account_id);
                return (
                  <tr key={t.id} className="border-b border-rule align-baseline">
                    <td className="tabular w-24 py-2 pr-3 text-[12px] text-ink-faint">
                      {shortDate(t.posted_date)}
                    </td>
                    <td className="max-w-0 truncate py-2 pr-3 text-[13px]"
                      title={t.description_raw}>
                      {t.description_raw}
                      {t.pending && <span className="text-attention"> · pending</span>}
                    </td>
                    <td className="hidden whitespace-nowrap py-2 pr-3 text-[12px] text-ink-muted md:table-cell">
                      {account
                        ? `${account.display_name}${account.mask ? ` ··${account.mask}` : ""}`
                        : "—"}
                    </td>
                    <td className="hidden py-2 pr-3 text-[11px] uppercase tracking-wide text-ink-faint sm:table-cell">
                      {sourceLabel(t)}
                    </td>
                    <td className="py-2 pr-3">
                      <select aria-label={`Category for ${t.description_raw}`}
                        value={t.category_id ?? ""}
                        className="max-w-[150px] border border-transparent bg-transparent py-0.5 text-[13px] text-ink-muted hover:border-rule-strong focus:border-ink"
                        onChange={(e) => setCategory(t, Number(e.target.value))}>
                        <option value="" disabled>Set category…</option>
                        {sortedCategories.map((c) => (
                          <option key={c.id} value={c.id}>{c.name}</option>
                        ))}
                      </select>
                    </td>
                    <td className="py-2 text-right">
                      <Money minor={t.amount_minor} className="text-[13px]" />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {hasMore && (
            <div className="py-4 text-center">
              <button type="button" disabled={loadingMore}
                onClick={async () => {
                  setLoadingMore(true);
                  await load(rows.length, true);
                  setLoadingMore(false);
                }}
                className="border border-rule-strong px-4 py-1.5 text-[13px] font-medium hover:border-ink disabled:opacity-50">
                {loadingMore ? "Loading…" : "Load more"}
              </button>
            </div>
          )}
        </>
      )}
    </>
  );
}
