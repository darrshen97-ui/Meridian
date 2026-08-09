// Money arrives from the API as integer minor units and stays integral here —
// formatting is string assembly, never float arithmetic (non-negotiable #7).

export function formatMinor(minor: number, opts?: { sign?: boolean }): string {
  const negative = minor < 0;
  const abs = Math.abs(minor);
  const whole = Math.floor(abs / 100).toLocaleString("en-US");
  const cents = String(abs % 100).padStart(2, "0");
  const sign = negative ? "−" : opts?.sign ? "+" : "";
  return `${sign}$${whole}.${cents}`;
}

export function formatCompactMinor(minor: number): string {
  const abs = Math.abs(minor);
  if (abs >= 100_000_00) {
    const whole = Math.floor(abs / 100_000_00);
    const tenth = Math.floor((abs % 100_000_00) / 10_000_00);
    return `${minor < 0 ? "−" : ""}$${whole}.${tenth}k`;
  }
  return formatMinor(minor);
}
