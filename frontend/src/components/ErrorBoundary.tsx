import { Component } from "react";
import type { ReactNode } from "react";

// A rendering crash must never be a blank screen (GridPilot lesson #4).
export class ErrorBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div className="mx-auto max-w-md px-6 py-24 text-center" role="alert">
        <p className="text-[17px] font-medium">This view hit an error and stopped.</p>
        <p className="mt-2 text-[13px] text-ink-muted">
          Your data is unaffected. Reload the page; if it happens again, the server
          log will say why.
        </p>
        <button type="button" onClick={() => window.location.reload()}
          className="mt-5 border border-rule-strong px-4 py-1.5 text-[13px] font-medium hover:border-ink">
          Reload
        </button>
      </div>
    );
  }
}
