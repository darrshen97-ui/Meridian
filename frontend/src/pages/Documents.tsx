import { useRef, useState } from "react";
import { api, ApiError } from "../api/client";
import type { Account, DocumentRow, Transaction } from "../api/types";
import { Money } from "../components/Money";
import { PageHeader } from "../components/PageHeader";
import { EmptyState, ErrorState, Loading, PartialNotice } from "../components/States";
import { shortDate, shortDateTime } from "../lib/dates";
import { useFetch } from "../lib/useFetch";

interface UploadResult {
  filename: string;
  status: "uploaded" | "rejected";
  error?: string;
  document?: DocumentRow;
}

interface Preview {
  parser: string;
  account_hint: { institution: string | null; mask: string | null;
    account_type: string | null };
  matched_accounts: Account[];
  transactions: { posted_date: string; description: string; amount_minor: number }[];
  period_start: string | null;
  period_end: string | null;
  problems: { page: number | null; line: string; reason: string }[];
  notes: string[];
}

const STATUS_LABEL: Record<string, string> = {
  pending: "Not imported", parsing: "Parsing", parsed: "Imported",
  partial: "Imported with skips", failed: "Failed",
};

export function Documents() {
  const documents = useFetch<DocumentRow[]>("/api/documents");
  const accounts = useFetch<Account[]>("/api/accounts");
  const [results, setResults] = useState<UploadResult[]>([]);
  const [uploading, setUploading] = useState(false);
  const [openId, setOpenId] = useState<number | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  async function upload(files: File[]) {
    if (files.length === 0) return;
    setUploading(true);
    try {
      const out = await api.uploadFiles<UploadResult[]>("/api/documents/upload", files);
      setResults(out);
      documents.reload();
    } catch (err) {
      setResults([{ filename: files.map((f) => f.name).join(", "),
        status: "rejected",
        error: err instanceof ApiError ? err.message : "The upload didn't reach the server." }]);
    } finally {
      setUploading(false);
    }
  }

  const accountById = new Map((accounts.data ?? []).map((a) => [a.id, a]));

  return (
    <>
      <PageHeader title="Documents"
        sub="Every uploaded statement, what it parsed to, and the transactions it produced." />

      <div
        role="button" tabIndex={0} aria-label="Upload statements"
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") inputRef.current?.click(); }}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          upload(Array.from(e.dataTransfer.files));
        }}
        className={`cursor-pointer border border-dashed px-6 py-8 text-center ${
          dragOver ? "border-accent bg-accent-wash" : "border-rule-strong"}`}>
        <p className="text-[15px] font-medium">
          {uploading ? "Uploading…" : "Drop statements here, or click to choose files"}
        </p>
        <p className="mt-1 text-[13px] text-ink-muted">
          PDF statements, Venmo / Cash App / Binance / Gemini CSV exports, and OFX or QFX files.
        </p>
        <input ref={inputRef} type="file" multiple hidden
          accept=".pdf,.csv,.ofx,.qfx"
          onChange={(e) => {
            upload(Array.from(e.target.files ?? []));
            e.target.value = "";
          }} />
      </div>

      {results.length > 0 && (
        <ul className="mt-3 space-y-1" aria-label="Upload results">
          {results.map((r, i) => (
            <li key={i} className="flex items-baseline gap-2 text-[13px]">
              <span className={`text-[11px] uppercase tracking-wide ${
                r.status === "uploaded" ? "text-positive" : "text-critical"}`}>
                {r.status}
              </span>
              <span className="truncate">{r.filename}</span>
              {r.error && <span className="text-ink-muted">— {r.error}</span>}
            </li>
          ))}
        </ul>
      )}

      <div className="mt-8">
        {documents.loading ? (
          <Loading label="Reading documents" />
        ) : documents.error ? (
          <ErrorState happened={documents.error} onRetry={documents.reload} />
        ) : (documents.data ?? []).length === 0 ? (
          <EmptyState title="No documents yet"
            body="Upload a statement above — you'll see exactly what it contains before anything is imported." />
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-rule-strong text-left text-[12px] text-ink-muted">
                <th className="py-2 pr-3 font-medium">File</th>
                <th className="hidden py-2 pr-3 font-medium sm:table-cell">Period</th>
                <th className="hidden py-2 pr-3 font-medium md:table-cell">Account</th>
                <th className="py-2 pr-3 font-medium">Status</th>
                <th className="hidden py-2 text-right font-medium sm:table-cell">Uploaded</th>
              </tr>
            </thead>
            <tbody>
              {(documents.data ?? []).map((d) => (
                <DocRow key={d.id} doc={d}
                  account={d.account_id ? accountById.get(d.account_id) : undefined}
                  open={openId === d.id}
                  onToggle={() => setOpenId(openId === d.id ? null : d.id)}
                  onImported={() => { documents.reload(); accounts.reload(); }} />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}

function DocRow({ doc, account, open, onToggle, onImported }: {
  doc: DocumentRow;
  account?: Account;
  open: boolean;
  onToggle: () => void;
  onImported: () => void;
}) {
  const imported = doc.account_id !== null && doc.parse_status !== "pending";
  return (
    <>
      <tr className="border-b border-rule">
        <td className="max-w-0 truncate py-2.5 pr-3 text-[13px]">
          <button type="button" onClick={onToggle}
            className="underline-offset-2 hover:underline" aria-expanded={open}>
            {doc.filename}
          </button>
        </td>
        <td className="tabular hidden whitespace-nowrap py-2.5 pr-3 text-[12px] text-ink-muted sm:table-cell">
          {doc.period_start && doc.period_end
            ? `${shortDate(doc.period_start)} – ${shortDate(doc.period_end)}`
            : "—"}
        </td>
        <td className="hidden whitespace-nowrap py-2.5 pr-3 text-[12px] text-ink-muted md:table-cell">
          {account ? `${account.display_name}${account.mask ? ` ··${account.mask}` : ""}` : "—"}
        </td>
        <td className={`whitespace-nowrap py-2.5 pr-3 text-[12px] ${
          doc.parse_status === "failed" ? "text-critical"
            : doc.parse_status === "partial" ? "text-attention" : "text-ink-muted"}`}>
          {STATUS_LABEL[doc.parse_status] ?? doc.parse_status}
        </td>
        <td className="hidden whitespace-nowrap py-2.5 text-right text-[11px] text-ink-faint sm:table-cell">
          {shortDateTime(doc.uploaded_at)}
        </td>
      </tr>
      {open && (
        <tr className="border-b border-rule bg-surface">
          <td colSpan={5} className="px-3 py-4">
            {imported
              ? <ImportedDetail doc={doc} />
              : <PreviewDetail doc={doc} onImported={onImported} />}
          </td>
        </tr>
      )}
    </>
  );
}

function ImportedDetail({ doc }: { doc: DocumentRow }) {
  const txns = useFetch<Transaction[]>(`/api/documents/${doc.id}/transactions`);
  if (txns.loading) return <Loading label="Reading transactions" />;
  if (txns.error) return <ErrorState happened={txns.error} onRetry={txns.reload} />;
  const rows = txns.data ?? [];
  return (
    <>
      {doc.parse_error && (
        <div className="mb-3"><PartialNotice>Skipped content: {doc.parse_error}</PartialNotice></div>
      )}
      <p className="pb-2 text-[12px] text-ink-muted">
        {rows.length.toLocaleString()} transaction{rows.length === 1 ? "" : "s"} from this
        document (rows that merged with live data count too).
      </p>
      <TxnTable rows={rows.map((t) => ({
        posted_date: t.posted_date, description: t.description_raw,
        amount_minor: t.amount_minor,
      }))} />
    </>
  );
}

function PreviewDetail({ doc, onImported }: { doc: DocumentRow; onImported: () => void }) {
  const preview = useFetch<Preview>(`/api/documents/${doc.id}/preview`);
  const accounts = useFetch<Account[]>("/api/accounts");
  const [choice, setChoice] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  if (preview.loading) return <Loading label="Parsing the document" />;
  if (preview.error) {
    return <ErrorState happened={preview.error}
      todo="The file may be unreadable — re-download it from your bank and upload again." />;
  }
  const p = preview.data!;
  const matchedIds = new Set(p.matched_accounts.map((a) => a.id));
  const selected = choice || (p.matched_accounts.length === 1
    ? String(p.matched_accounts[0].id) : "");

  async function importNow() {
    setBusy(true);
    setMessage(null);
    try {
      const body = selected === "create"
        ? { create_account: true }
        : { account_id: Number(selected) };
      const result = await api.post<{ imported: number; merged: number }>(
        `/api/documents/${doc.id}/import`, body);
      setMessage(`Imported ${result.imported} transaction${result.imported === 1 ? "" : "s"}` +
        (result.merged > 0 ? `, merged ${result.merged} with existing rows.` : "."));
      onImported();
    } catch (err) {
      setMessage(err instanceof ApiError ? err.message : "The import didn't complete.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="flex flex-wrap items-baseline gap-x-6 gap-y-1 pb-3 text-[12px] text-ink-muted">
        <span>Detected: {p.account_hint.institution ?? "unknown institution"}
          {p.account_hint.mask ? ` · ending ${p.account_hint.mask}` : ""}
          {p.account_hint.account_type ? ` · ${p.account_hint.account_type.replace("_", " ")}` : ""}
        </span>
        {p.period_start && p.period_end && (
          <span className="tabular">{shortDate(p.period_start)} – {shortDate(p.period_end)}</span>
        )}
        <span>{p.transactions.length.toLocaleString()} transactions found</span>
      </div>

      {p.notes.map((n, i) => <div key={i} className="mb-2"><PartialNotice>{n}</PartialNotice></div>)}
      {p.problems.length > 0 && (
        <div className="mb-2">
          <PartialNotice>
            {p.problems.length} row{p.problems.length === 1 ? "" : "s"} couldn't be read —
            first: {p.problems[0].reason} {p.problems[0].page && `(page ${p.problems[0].page})`}
          </PartialNotice>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2 pb-3">
        <label htmlFor={`acct-${doc.id}`} className="text-[13px] text-ink-muted">
          Import into
        </label>
        <select id={`acct-${doc.id}`} value={selected}
          onChange={(e) => setChoice(e.target.value)}
          className="border border-rule-strong bg-surface px-2 py-1 text-[13px] focus:border-ink">
          <option value="" disabled>Choose an account…</option>
          {(accounts.data ?? []).map((a) => (
            <option key={a.id} value={a.id}>
              {a.display_name}{a.mask ? ` ··${a.mask}` : ""}
              {matchedIds.has(a.id) ? " — matches this statement" : ""}
            </option>
          ))}
          <option value="create">Create a new account from this statement</option>
        </select>
        <button type="button" disabled={busy || !selected} onClick={importNow}
          className="bg-accent px-4 py-1.5 text-[13px] font-medium text-surface disabled:opacity-50">
          {busy ? "Importing…" : "Import"}
        </button>
        {message && <span role="status" className="text-[13px] text-ink-muted">{message}</span>}
      </div>

      <p className="pb-1 text-[12px] text-ink-faint">
        Nothing is written until you import. Preview below.
      </p>
      <TxnTable rows={p.transactions.slice(0, 25)} />
      {p.transactions.length > 25 && (
        <p className="pt-1 text-[12px] text-ink-faint">
          …and {p.transactions.length - 25} more, all included in the import.
        </p>
      )}
    </>
  );
}

function TxnTable({ rows }: {
  rows: { posted_date: string; description: string; amount_minor: number }[];
}) {
  return (
    <table className="w-full">
      <tbody>
        {rows.map((t, i) => (
          <tr key={i} className="border-b border-rule">
            <td className="tabular w-24 py-1.5 pr-3 text-[12px] text-ink-faint">
              {shortDate(t.posted_date)}
            </td>
            <td className="max-w-0 truncate py-1.5 pr-3 text-[13px]">{t.description}</td>
            <td className="py-1.5 text-right">
              <Money minor={t.amount_minor} className="text-[13px]" />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
