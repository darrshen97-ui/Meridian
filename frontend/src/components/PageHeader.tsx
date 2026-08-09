export function PageHeader({ title, sub, actions }: {
  title: string;
  sub?: string;
  actions?: React.ReactNode;
}) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-4 pb-4">
      <div>
        <h1 className="text-[24px] font-semibold leading-tight">{title}</h1>
        {sub && <p className="mt-1 text-[13px] text-ink-muted">{sub}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </header>
  );
}
