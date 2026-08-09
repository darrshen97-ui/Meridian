import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

const NAV = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/accounts", label: "Accounts" },
  { to: "/transactions", label: "Transactions" },
  { to: "/review", label: "Review" },
  { to: "/reconciliation", label: "Reconciliation" },
  { to: "/documents", label: "Documents" },
  { to: "/coach", label: "Coach" },
  { to: "/budgets", label: "Budgets" },
  { to: "/settings", label: "Settings" },
];

export function Shell() {
  const { me, logout } = useAuth();
  const navigate = useNavigate();

  async function switchProfile() {
    await logout();               // switching profiles requires re-authentication (§8)
    navigate("/");
  }

  const link = ({ isActive }: { isActive: boolean }) =>
    [
      "block px-3 py-1.5 text-[13px] leading-6 border-l-2 -ml-px",
      isActive
        ? "border-accent font-medium text-ink"
        : "border-transparent text-ink-muted hover:text-ink",
    ].join(" ");

  return (
    <div className="mx-auto flex min-h-screen max-w-[1240px]">
      <aside className="hidden w-[184px] shrink-0 border-r border-rule px-4 py-6 md:block">
        <p className="px-3 pb-6 text-[15px] font-semibold tracking-tight">Meridian</p>
        <nav aria-label="Primary" className="border-l border-rule">
          {NAV.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end} className={link}>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-10 border-t border-rule px-3 pt-4">
          <p className="truncate text-[12px] text-ink-muted">{me?.display_name}</p>
          <button type="button" onClick={switchProfile}
            className="mt-1 text-[12px] text-ink-faint underline-offset-2 hover:text-ink hover:underline">
            Switch profile
          </button>
        </div>
      </aside>

      <div className="min-w-0 flex-1">
        {/* Small screens: the nav becomes a scrollable top bar. */}
        <div className="border-b border-rule md:hidden">
          <div className="flex items-center justify-between px-4 pt-3">
            <p className="text-[15px] font-semibold">Meridian</p>
            <button type="button" onClick={switchProfile}
              className="text-[12px] text-ink-faint">
              {me?.display_name} · switch
            </button>
          </div>
          <nav aria-label="Primary" className="flex gap-1 overflow-x-auto px-2 py-1">
            {NAV.map((item) => (
              <NavLink key={item.to} to={item.to} end={item.end}
                className={({ isActive }) =>
                  [
                    "whitespace-nowrap px-2 py-1 text-[13px] border-b-2",
                    isActive ? "border-accent text-ink" : "border-transparent text-ink-muted",
                  ].join(" ")}>
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>

        <main className="px-4 py-6 md:px-8 md:py-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
