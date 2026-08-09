import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "../api/client";
import type { Category } from "../api/types";
import { Money } from "../components/Money";
import { PageHeader } from "../components/PageHeader";
import { EmptyState, ErrorState, Loading, PartialNotice } from "../components/States";
import { shortDate } from "../lib/dates";
import { useFetch } from "../lib/useFetch";

interface QueueItem {
  id: number;
  posted_date: string;
  description: string;
  merchant: string | null;
  amount_minor: number;
  suggested_category_id: number | null;
  suggested_category: string | null;
  confidence: number | null;
}

interface Queue {
  total: number;
  items: QueueItem[];
}

interface RunSummary {
  examined: number;
  rules_applied: number;
  llm_applied: number;
  llm_suggested: number;
  sent_to_model: number;
  model_unavailable: boolean;
  model_message: string | null;
  few_shot_hit_rate: number | null;
}

export function Review() {
  const queue = useFetch<Queue>("/api/review?limit=200");
  const categories = useFetch<Category[]>("/api/categories");
  const [selected, setSelected] = useState(0);
  const [running, setRunning] = useState(false);
  const [summary, setSummary] = useState<RunSummary | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const listRef = useRef<HTMLTableSectionElement>(null);

  const items = queue.data?.items ?? [];

  const resolve = useCallback(async (item: QueueItem, categoryId: number,
                                     applyToMatching: boolean) => {
    try {
      const result = await api.post<{ resolved: number; category: string }>(
        `/api/review/${item.id}/resolve`,
        { category_id: categoryId, apply_to_matching: applyToMatching });
      setNotice(result.resolved > 1
        ? `Filed ${result.resolved} matching transactions under ${result.category}.`
        : `Filed under ${result.category}.`);
      queue.reload();
    } catch (err) {
      setNotice(err instanceof ApiError ? err.message : "That didn't save.");
    }
  }, [queue]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.target instanceof HTMLElement &&
          ["INPUT", "SELECT", "TEXTAREA"].includes(e.target.tagName)) return;
      const item = items[selected];
      if (e.key === "j" || e.key === "ArrowDown") {
        e.preventDefault();
        setSelected((s) => Math.min(s + 1, items.length - 1));
      } else if (e.key === "k" || e.key === "ArrowUp") {
        e.preventDefault();
        setSelected((s) => Math.max(s - 1, 0));
      } else if ((e.key === "a" || e.key === "Enter") && item?.suggested_category_id) {
        e.preventDefault();
        resolve(item, item.suggested_category_id, false);
      } else if (e.key === "A" && item?.suggested_category_id) {
        e.preventDefault();
        resolve(item, item.suggested_category_id, true);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [items, selected, resolve]);

  useEffect(() => {
    setSelected((s) => Math.min(s, Math.max(items.length - 1, 0)));
  }, [items.length]);

  async function runCategorization() {
    setRunning(true);
    setSummary(null);
    try {
      setSummary(await api.post<RunSummary>("/api/categorize/run", { limit: 5000 }));
      queue.reload();
    } catch (err) {
      setNotice(err instanceof ApiError ? err.message : "Categorization didn't run.");
    } finally {
      setRunning(false);
    }
  }

  const sortedCategories = (categories.data ?? [])
    .slice().sort((a, b) => a.name.localeCompare(b.name));

  return (
    <>
      <PageHeader title="Review queue"
        sub={queue.data ? `${queue.data.total.toLocaleString()} transactions waiting` : undefined}
        actions={
          <button type="button" onClick={runCategorization} disabled={running}
            className="border border-rule-strong px-4 py-1.5 text-[13px] font-medium hover:border-ink disabled:opacity-50">
            {running ? "Categorizing…" : "Run categorization"}
          </button>
        } />

      {summary && (
        <div className="mb-4 border-b border-rule pb-3 text-[13px] text-ink-muted">
          <p>
            Examined {summary.examined.toLocaleString()} · rules filed{" "}
            {summary.rules_applied.toLocaleString()} · model filed{" "}
            {summary.llm_applied.toLocaleString()} · suggested{" "}
            {summary.llm_suggested.toLocaleString()} for review
            {summary.few_shot_hit_rate !== null &&
              ` · your corrections informed ${Math.round(summary.few_shot_hit_rate * 100)}% of model rows`}
          </p>
          {summary.model_unavailable && (
            <ModelUnavailable message={summary.model_message} />
          )}
        </div>
      )}
      {notice && <div className="mb-3"><PartialNotice>{notice}</PartialNotice></div>}

      {queue.loading ? (
        <Loading label="Reading the queue" />
      ) : queue.error ? (
        <ErrorState happened={queue.error} onRetry={queue.reload} />
      ) : items.length === 0 ? (
        <EmptyState title="Nothing waiting for review"
          body="Run categorization after a sync or an import — anything the rules and the model aren't sure about lands here." />
      ) : (
        <>
          <table className="w-full">
            <thead>
              <tr className="border-b border-rule-strong text-left text-[12px] text-ink-muted">
                <th className="py-2 pr-3 font-medium">Date</th>
                <th className="py-2 pr-3 font-medium">Description</th>
                <th className="py-2 pr-3 font-medium">Suggestion</th>
                <th className="py-2 pr-3 font-medium">File under</th>
                <th className="py-2 text-right font-medium">Amount</th>
              </tr>
            </thead>
            <tbody ref={listRef}>
              {items.map((item, index) => (
                <tr key={item.id}
                  className={`border-b border-rule align-baseline ${
                    index === selected ? "bg-accent-wash" : ""}`}
                  onClick={() => setSelected(index)}>
                  <td className="tabular w-24 py-2 pr-3 text-[12px] text-ink-faint">
                    {shortDate(item.posted_date)}
                  </td>
                  <td className="max-w-0 truncate py-2 pr-3 text-[13px]">
                    {item.description}
                  </td>
                  <td className="whitespace-nowrap py-2 pr-3 text-[12px] text-ink-muted">
                    {item.suggested_category
                      ? <>
                          {item.suggested_category}
                          {item.confidence !== null && (
                            <span className="text-ink-faint">
                              {" "}· {Math.round(item.confidence * 100)}%
                            </span>
                          )}
                        </>
                      : <span className="text-ink-faint">none</span>}
                  </td>
                  <td className="py-2 pr-3">
                    <div className="flex items-center gap-1.5">
                      {item.suggested_category_id && (
                        <button type="button"
                          onClick={() => resolve(item, item.suggested_category_id!, false)}
                          className="border border-rule-strong px-2 py-0.5 text-[12px] hover:border-ink"
                          title="Accept suggestion (a)">
                          Accept
                        </button>
                      )}
                      <select aria-label={`Category for ${item.description}`}
                        value=""
                        className="max-w-[130px] border border-transparent bg-transparent py-0.5 text-[12px] text-ink-muted hover:border-rule-strong focus:border-ink"
                        onChange={(e) => resolve(item, Number(e.target.value),
                          e.target.selectedOptions[0].dataset.bulk === "1")}>
                        <option value="" disabled>Pick…</option>
                        {sortedCategories.map((c) => (
                          <option key={c.id} value={c.id}>{c.name}</option>
                        ))}
                        <optgroup label="Apply to all matching">
                          {sortedCategories.map((c) => (
                            <option key={`b${c.id}`} value={c.id} data-bulk="1">
                              {c.name} — all matching
                            </option>
                          ))}
                        </optgroup>
                      </select>
                    </div>
                  </td>
                  <td className="py-2 text-right">
                    <Money minor={item.amount_minor} className="text-[13px]" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="pt-3 text-[12px] text-ink-faint">
            Keyboard: <kbd>j</kbd>/<kbd>k</kbd> move · <kbd>a</kbd> accept suggestion ·{" "}
            <kbd>Shift+A</kbd> accept for every matching merchant.
          </p>
        </>
      )}
    </>
  );
}

export function ModelUnavailable({ message }: { message: string | null }) {
  const command = /`([^`]+)`/.exec(message ?? "")?.[1] ?? "ollama pull qwen2.5:7b-instruct";
  const [copied, setCopied] = useState(false);
  return (
    <div className="mt-2 border-l-2 border-rule-strong pl-3">
      <p className="text-[13px]">
        The local model isn't available, so only rule-based filing ran.
        Everything else works normally.
      </p>
      <p className="mt-1 text-[13px] text-ink-muted">
        To enable AI features: install Ollama, then run{" "}
        <code className="tabular text-[12px]">{command}</code>
        <button type="button"
          onClick={() => {
            navigator.clipboard.writeText(command);
            setCopied(true);
            setTimeout(() => setCopied(false), 1500);
          }}
          className="ml-2 border border-rule-strong px-2 py-0.5 text-[12px] hover:border-ink">
          {copied ? "Copied" : "Copy"}
        </button>
      </p>
    </div>
  );
}
