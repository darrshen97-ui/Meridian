import { formatMinor } from "../lib/money";

// Money in is the accent green; money out is ink, never red (§13).
export function Money({ minor, signed = false, className = "" }: {
  minor: number;
  signed?: boolean;
  className?: string;
}) {
  const color = minor > 0 ? "text-positive" : "text-negative";
  return (
    <span className={`tabular ${color} ${className}`}>
      {formatMinor(minor, { sign: signed })}
    </span>
  );
}
