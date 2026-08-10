// §17: smoke-render every route. Fetch and EventSource are stubbed with empty
// datasets, so each page must survive its loading→empty path without crashing.
// @vitest-environment jsdom
import { render, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "./auth";
import { Shell } from "./components/Shell";
import { Accounts } from "./pages/Accounts";
import { Budgets } from "./pages/Budgets";
import { Coach } from "./pages/Coach";
import { Dashboard } from "./pages/Dashboard";
import { Documents } from "./pages/Documents";
import { Reconciliation } from "./pages/Reconciliation";
import { Review } from "./pages/Review";
import { Settings } from "./pages/Settings";
import { Transactions } from "./pages/Transactions";

const EMPTY_BY_PATH: Record<string, unknown> = {
  "/api/auth/me": { id: 1, display_name: "Test User", email: "t@example.com" },
  "/api/dashboard": {
    as_of: "2026-08-10", spending_power_minor: 0, liquid_minor: 0,
    obligations_minor: 0, liquid_accounts: [], card_balances: [],
    this_month: { label: "August 2026", spent_minor: 0, income_minor: 0 },
    last_month: { label: "July 2026", spent_minor: 0, income_minor: 0 },
    needs_attention: { review_count: 0, unresolved_findings: 0 }, recent: [],
  },
  "/api/sync/status": { provider: "mock", last_run: null },
  "/api/review": { total: 0, items: [] },
  "/api/budgets/overview": {
    period: "2026-08", entries: [], uncategorized_minor: 0,
    totals: { target_minor: 0, actual_minor: 0 },
  },
  "/api/ai/status": {
    provider: "ollama", endpoint: "http://127.0.0.1:11434",
    endpoint_is_local: true, model: "qwen2.5:7b-instruct", reachable: false,
    model_present: false, models: [], sends_data_off_device: false,
    last_call: null,
    totals: { calls: 0, input_tokens: 0, output_tokens: 0, avg_latency_ms: null },
    enable_hint: "Install Ollama, then run: ollama pull qwen2.5:7b-instruct",
  },
};

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input).split("?")[0];
    const body = EMPTY_BY_PATH[path] ?? [];
    return new Response(JSON.stringify(body), {
      status: 200, headers: { "Content-Type": "application/json" },
    });
  }));
  vi.stubGlobal("EventSource", class {
    addEventListener() {}
    removeEventListener() {}
    close() {}
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

const ROUTES: [string, string, React.ReactElement, RegExp][] = [
  ["/", "Dashboard", <Dashboard />, /Spending power|Reading your accounts/],
  ["/accounts", "Accounts", <Accounts />, /Accounts/],
  ["/transactions", "Transactions", <Transactions />, /Transactions/],
  ["/review", "Review", <Review />, /Review queue/],
  ["/reconciliation", "Reconciliation", <Reconciliation />, /Reconciliation/],
  ["/documents", "Documents", <Documents />, /Documents/],
  ["/coach", "Coach", <Coach />, /Coach/],
  ["/budgets", "Budgets", <Budgets />, /Budgets & Simulator/],
  ["/settings", "Settings", <Settings />, /Settings/],
];

describe("every route smoke-renders inside the shell", () => {
  it.each(ROUTES)("%s (%s)", async (path, _name, element, expected) => {
    const { container } = render(
      <AuthProvider>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route element={<Shell />}>
              <Route path={path === "/" ? "/" : path.slice(1)} element={element} />
            </Route>
          </Routes>
        </MemoryRouter>
      </AuthProvider>,
    );
    await waitFor(() => expect(container.textContent).toMatch(expected));
    // No route may render an empty screen.
    expect((container.textContent ?? "").length).toBeGreaterThan(20);
  });
});
