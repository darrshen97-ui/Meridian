import { useRef, useState } from "react";
import { api, ApiError } from "../api/client";
import { Money } from "../components/Money";
import { PageHeader } from "../components/PageHeader";
import { Loading } from "../components/States";
import { shortDate } from "../lib/dates";
import { useFetch } from "../lib/useFetch";
import { ModelUnavailable } from "./Review";

interface ToolCall {
  tool: string;
  arguments: Record<string, unknown>;
  computed_total: string | null;
  count: number | null;
}

interface SourceTxn {
  id: number;
  posted_date: string;
  description: string;
  amount_minor: number;
}

interface CoachResponse {
  available: boolean;
  message: string | null;
  answer: string | null;
  tool_calls: ToolCall[];
  transactions: SourceTxn[];
}

interface ChatEntry {
  role: "user" | "coach";
  content: string;
  toolCalls?: ToolCall[];
  transactions?: SourceTxn[];
}

const SUGGESTIONS = [
  "What did I spend on dining last month?",
  "Why was December so expensive?",
  "Can I afford a $1,200 purchase right now?",
  "What subscriptions am I paying for?",
];

export function Coach() {
  const aiStatus = useFetch<{ model_present: boolean; reachable: boolean;
    endpoint_is_local: boolean; enable_hint: string | null }>("/api/ai/status");
  const [chat, setChat] = useState<ChatEntry[]>([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  const unavailable = aiStatus.data &&
    (!aiStatus.data.reachable || !aiStatus.data.model_present ||
     !aiStatus.data.endpoint_is_local);

  async function ask(text: string) {
    const q = text.trim();
    if (!q || busy) return;
    setQuestion("");
    setChat((c) => [...c, { role: "user", content: q }]);
    setBusy(true);
    try {
      const history = chat.slice(-6).map((e) => ({
        role: e.role === "coach" ? "assistant" : "user", content: e.content,
      }));
      const resp = await api.post<CoachResponse>("/api/coach/ask",
        { question: q, history });
      if (!resp.available) {
        setChat((c) => [...c, {
          role: "coach",
          content: resp.message ?? "The local model isn't available right now.",
        }]);
      } else {
        setChat((c) => [...c, {
          role: "coach", content: resp.answer ?? "",
          toolCalls: resp.tool_calls, transactions: resp.transactions,
        }]);
      }
    } catch (err) {
      setChat((c) => [...c, {
        role: "coach",
        content: err instanceof ApiError ? err.message
          : "The server can't be reached.",
      }]);
    } finally {
      setBusy(false);
      setTimeout(() => endRef.current?.scrollIntoView({ block: "end" }), 50);
    }
  }

  return (
    <>
      <PageHeader title="Coach"
        sub="Answers come from queries against your real ledger — every answer shows what it looked at." />

      {aiStatus.loading ? (
        <Loading label="Checking the model" />
      ) : unavailable ? (
        <div className="max-w-xl">
          <p className="text-[15px] font-medium">The coach needs the local model</p>
          <p className="mt-1 text-[13px] text-ink-muted">
            Everything else in Meridian works without it. Rules-based categorization
            still runs; only conversational answers are off.
          </p>
          <ModelUnavailable message={aiStatus.data?.enable_hint ?? null} />
        </div>
      ) : (
        <div className="mx-auto flex max-w-2xl flex-col">
          {chat.length === 0 && (
            <div className="border-t border-rule pt-6">
              <p className="text-[13px] text-ink-muted">Try asking:</p>
              <ul className="mt-2 space-y-1.5">
                {SUGGESTIONS.map((s) => (
                  <li key={s}>
                    <button type="button" onClick={() => ask(s)}
                      className="text-left text-[13px] text-accent underline-offset-2 hover:underline">
                      {s}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="space-y-5">
            {chat.map((entry, i) => (
              <div key={i}>
                {entry.role === "user" ? (
                  <p className="border-l-2 border-rule-strong pl-3 text-[13px] text-ink-muted">
                    {entry.content}
                  </p>
                ) : (
                  <div>
                    <p className="whitespace-pre-wrap text-[15px]">{entry.content}</p>
                    {entry.toolCalls && entry.toolCalls.length > 0 && (
                      <Sources toolCalls={entry.toolCalls}
                        transactions={entry.transactions ?? []} />
                    )}
                  </div>
                )}
              </div>
            ))}
            {busy && <Loading label="Querying your ledger" />}
            <div ref={endRef} />
          </div>

          <form className="mt-6 flex gap-2 border-t border-rule pt-4"
            onSubmit={(e) => { e.preventDefault(); ask(question); }}>
            <input value={question} onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask about your spending"
              aria-label="Ask the coach"
              className="flex-1 border border-rule-strong bg-surface px-3 py-2 text-[15px] placeholder:text-ink-faint focus:border-ink" />
            <button type="submit" disabled={busy || !question.trim()}
              className="bg-accent px-4 py-2 text-[15px] font-medium text-surface disabled:opacity-50">
              Ask
            </button>
          </form>
        </div>
      )}
    </>
  );
}

function Sources({ toolCalls, transactions }: {
  toolCalls: ToolCall[];
  transactions: SourceTxn[];
}) {
  const [open, setOpen] = useState(false);
  const totals = toolCalls.filter((c) => c.computed_total);
  return (
    <div className="mt-2 border-l-2 border-rule pl-3">
      {totals.length > 0 && (
        <p className="tabular text-[12px] text-ink-muted">
          {totals.map((c, i) => (
            <span key={i}>
              Queried total: {c.computed_total}
              {c.count !== null && ` across ${c.count} transactions`}
              {i < totals.length - 1 ? " · " : ""}
            </span>
          ))}
        </p>
      )}
      <button type="button" onClick={() => setOpen(!open)}
        className="text-[12px] text-ink-faint underline-offset-2 hover:text-ink hover:underline"
        aria-expanded={open}>
        {open ? "Hide" : "Show"} what the coach looked at
        ({toolCalls.length} {toolCalls.length === 1 ? "query" : "queries"},{" "}
        {transactions.length} transactions)
      </button>
      {open && (
        <div className="mt-2">
          <ul className="space-y-0.5 text-[12px] text-ink-muted">
            {toolCalls.map((c, i) => (
              <li key={i} className="tabular truncate">
                {c.tool}({Object.entries(c.arguments)
                  .map(([k, v]) => `${k}=${String(v)}`).join(", ")})
              </li>
            ))}
          </ul>
          {transactions.length > 0 && (
            <table className="mt-2 w-full">
              <tbody>
                {transactions.slice(0, 15).map((t) => (
                  <tr key={t.id} className="border-b border-rule">
                    <td className="tabular w-24 py-1 pr-3 text-[12px] text-ink-faint">
                      {shortDate(t.posted_date)}
                    </td>
                    <td className="max-w-0 truncate py-1 pr-3 text-[12px]">
                      {t.description}
                    </td>
                    <td className="py-1 text-right">
                      <Money minor={t.amount_minor} className="text-[12px]" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
