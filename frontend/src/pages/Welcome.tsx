import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { Profile } from "../api/types";
import { useAuth } from "../auth";
import { Loading } from "../components/States";

type Mode = { view: "list" } | { view: "login"; profile: Profile } | { view: "create" };

// zxcvbn-style guidance without the dictionary: length + variety heuristic.
function strength(password: string): { label: string; ok: boolean } {
  if (password.length === 0) return { label: "", ok: false };
  if (password.length < 10) return { label: "Too short — 10 characters minimum", ok: false };
  const classes =
    Number(/[a-z]/.test(password)) + Number(/[A-Z]/.test(password)) +
    Number(/\d/.test(password)) + Number(/[^A-Za-z0-9]/.test(password));
  const long = password.length >= 14;
  if (long && classes >= 2) return { label: "Strong", ok: true };
  if (classes >= 3 || long) return { label: "Good", ok: true };
  return { label: "Fair — longer is stronger", ok: true };
}

const field =
  "w-full border border-rule-strong bg-surface px-3 py-2 text-[15px] " +
  "placeholder:text-ink-faint focus:border-ink";
const primaryBtn =
  "w-full bg-accent px-4 py-2 text-[15px] font-medium text-surface " +
  "disabled:opacity-50";
const quietBtn = "text-[13px] text-ink-muted underline-offset-2 hover:text-ink hover:underline";

export function Welcome() {
  const { login, register } = useAuth();
  const [profiles, setProfiles] = useState<Profile[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [mode, setMode] = useState<Mode>({ view: "list" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get<Profile[]>("/api/auth/profiles")
      .then((p) => {
        setProfiles(p);
        if (p.length === 0) setMode({ view: "create" });  // first run
      })
      .catch(() => setFailed(true));
  }, []);

  async function submit(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The server can't be reached.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-sm flex-col justify-center px-6 py-12">
      <h1 className="text-[32px] font-semibold tracking-tight">Meridian</h1>
      <p className="mt-1 text-[13px] text-ink-muted">
        Accounts, statements, and an honest read on your money.
      </p>

      <div className="mt-10 border-t border-rule pt-6">
        {failed ? (
          <p role="alert" className="text-[13px] text-critical">
            The Meridian server isn't responding. Start it, then reload this page.
          </p>
        ) : profiles === null ? (
          <Loading label="Finding profiles" />
        ) : mode.view === "list" ? (
          <>
            <p className="pb-2 text-[12px] uppercase tracking-wide text-ink-faint">
              Choose a profile
            </p>
            <ul className="border-t border-rule">
              {profiles.map((p) => (
                <li key={p.id} className="border-b border-rule">
                  <button type="button"
                    onClick={() => { setError(null); setMode({ view: "login", profile: p }); }}
                    className="flex w-full items-baseline justify-between px-1 py-3 text-left hover:bg-surface">
                    <span className="text-[15px] font-medium">{p.display_name}</span>
                    <span className="text-[12px] text-ink-faint">{p.email}</span>
                  </button>
                </li>
              ))}
            </ul>
            <div className="pt-4">
              <button type="button" className={quietBtn}
                onClick={() => { setError(null); setMode({ view: "create" }); }}>
                Create a new profile
              </button>
            </div>
          </>
        ) : mode.view === "login" ? (
          <LoginForm profile={mode.profile} busy={busy} error={error}
            onBack={() => { setError(null); setMode({ view: "list" }); }}
            onSubmit={(password) => submit(() => login(mode.profile.email, password))} />
        ) : (
          <CreateForm busy={busy} error={error}
            hasProfiles={profiles.length > 0}
            onBack={() => { setError(null); setMode({ view: "list" }); }}
            onSubmit={(name, email, password) =>
              submit(() => register(name, email, password))} />
        )}
      </div>
    </div>
  );
}

function LoginForm({ profile, busy, error, onBack, onSubmit }: {
  profile: Profile;
  busy: boolean;
  error: string | null;
  onBack: () => void;
  onSubmit: (password: string) => void;
}) {
  const [password, setPassword] = useState("");
  return (
    <form onSubmit={(e) => { e.preventDefault(); onSubmit(password); }}>
      <p className="text-[15px] font-medium">{profile.display_name}</p>
      <p className="text-[12px] text-ink-faint">{profile.email}</p>
      <label className="mt-4 block text-[13px] text-ink-muted" htmlFor="pw">Password</label>
      <input id="pw" type="password" autoFocus value={password} className={field}
        onChange={(e) => setPassword(e.target.value)} />
      {error && <p role="alert" className="mt-2 text-[13px] text-critical">{error}</p>}
      <button type="submit" disabled={busy || !password} className={`mt-4 ${primaryBtn}`}>
        {busy ? "Signing in…" : "Sign in"}
      </button>
      <div className="pt-3 text-center">
        <button type="button" onClick={onBack} className={quietBtn}>All profiles</button>
      </div>
    </form>
  );
}

function CreateForm({ busy, error, hasProfiles, onBack, onSubmit }: {
  busy: boolean;
  error: string | null;
  hasProfiles: boolean;
  onBack: () => void;
  onSubmit: (name: string, email: string, password: string) => void;
}) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const meter = strength(password);
  return (
    <form onSubmit={(e) => { e.preventDefault(); onSubmit(name, email, password); }}>
      <p className="text-[15px] font-medium">
        {hasProfiles ? "Create a profile" : "Create your first profile"}
      </p>
      <label className="mt-4 block text-[13px] text-ink-muted" htmlFor="nm">Display name</label>
      <input id="nm" autoFocus value={name} className={field}
        onChange={(e) => setName(e.target.value)} />
      <label className="mt-3 block text-[13px] text-ink-muted" htmlFor="em">Email</label>
      <input id="em" type="email" value={email} className={field}
        onChange={(e) => setEmail(e.target.value)} />
      <label className="mt-3 block text-[13px] text-ink-muted" htmlFor="cpw">
        Password <span className="text-ink-faint">(10 characters or more)</span>
      </label>
      <input id="cpw" type="password" value={password} className={field}
        onChange={(e) => setPassword(e.target.value)} />
      {meter.label && (
        <p className={`mt-1 text-[12px] ${meter.ok ? "text-ink-muted" : "text-attention"}`}>
          {meter.label}
        </p>
      )}
      {error && <p role="alert" className="mt-2 text-[13px] text-critical">{error}</p>}
      <button type="submit" disabled={busy || !name || !email || !meter.ok}
        className={`mt-4 ${primaryBtn}`}>
        {busy ? "Creating…" : "Create profile"}
      </button>
      {hasProfiles && (
        <div className="pt-3 text-center">
          <button type="button" onClick={onBack} className={quietBtn}>All profiles</button>
        </div>
      )}
    </form>
  );
}
