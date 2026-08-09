import { EmptyState } from "./States";

// Honest placeholder (non-negotiable #6): unbuilt features say so plainly.
export function NotBuilt({ feature, milestone }: { feature: string; milestone: number }) {
  return (
    <EmptyState
      title={`${feature} isn't built yet`}
      body={`It arrives with milestone ${milestone} of the build plan. Nothing here is stubbed or simulated — the view will appear when the feature is real.`}
    />
  );
}
