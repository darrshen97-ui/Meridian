import { useEffect, useState } from "react";

// Milestone 1 shell. The real application shell — navigation, design system,
// all five view states — lands in milestone 7 per docs/BUILD_PLAN.md.
export default function App() {
  const [health, setHealth] = useState<string>("checking");

  useEffect(() => {
    fetch("/health")
      .then((r) => r.json())
      .then((b) => setHealth(`server ok · v${b.version}`))
      .catch(() => setHealth("server unreachable"));
  }, []);

  return (
    <main className="mx-auto max-w-[1240px] px-8 py-16">
      <h1 className="text-[24px] font-semibold">Meridian</h1>
      <p className="mt-2 text-[15px] text-ink-muted">
        Build in progress — milestone 1 scaffold.
      </p>
      <p className="mt-8 border-t border-rule pt-4 text-[13px] text-ink-faint tabular">
        {health}
      </p>
    </main>
  );
}
