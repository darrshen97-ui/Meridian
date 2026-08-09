// The five required view states (§13): loading, empty, partial, error, populated.
// Loading is quiet and honest — no skeleton shimmer. Empty states invite action.
// Errors state what happened and what to do, in the interface's voice. No "Oops".

export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div aria-busy="true" className="border-t border-rule py-10 text-center">
      <p className="text-[13px] text-ink-faint">{label}…</p>
    </div>
  );
}

export function EmptyState({ title, body, action }: {
  title: string;
  body?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="border-t border-rule py-12 text-center">
      <p className="text-[15px] font-medium">{title}</p>
      {body && <p className="mx-auto mt-1 max-w-md text-[13px] text-ink-muted">{body}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorState({ happened, todo, onRetry }: {
  happened: string;
  todo?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="border-t border-rule py-10 text-center" role="alert">
      <p className="text-[15px] font-medium text-critical">{happened}</p>
      {todo && <p className="mt-1 text-[13px] text-ink-muted">{todo}</p>}
      {onRetry && (
        <button type="button" onClick={onRetry}
          className="mt-4 border border-rule-strong px-4 py-1.5 text-[13px] font-medium hover:border-ink">
          Try again
        </button>
      )}
    </div>
  );
}

export function PartialNotice({ children }: { children: React.ReactNode }) {
  return (
    <div className="border-l-2 border-attention bg-surface px-3 py-2 text-[13px] text-ink-muted"
      role="status">
      {children}
    </div>
  );
}
