// Appearance: follows the OS by default; Settings can pin light/dark later.
export type ThemePreference = "system" | "light" | "dark";

const STORAGE_KEY = "meridian-theme";

export function themePreference(): ThemePreference {
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored === "light" || stored === "dark" ? stored : "system";
}

export function setThemePreference(pref: ThemePreference): void {
  if (pref === "system") localStorage.removeItem(STORAGE_KEY);
  else localStorage.setItem(STORAGE_KEY, pref);
  apply();
}

function apply(): void {
  const pref = themePreference();
  const systemDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const dark = pref === "dark" || (pref === "system" && systemDark);
  document.documentElement.classList.toggle("dark", dark);
}

export function initTheme(): void {
  apply();
  window.matchMedia("(prefers-color-scheme: dark)")
    .addEventListener("change", apply);
}
