const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function shortDate(iso: string): string {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return `${MONTHS[m - 1]} ${d}, ${y}`;
}

export function shortDateTime(iso: string): string {
  const date = new Date(iso);
  return `${shortDate(iso)} · ${date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}`;
}
