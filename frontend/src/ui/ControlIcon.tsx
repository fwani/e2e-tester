/**
 * 출처: Application-owned SVG — shared workspace control geometry, no external icon library.
 */
export type ControlIconName = "close" | "more" | "options" | "collapse" | "expand";

/** Shared stroke and view box for compact workspace controls. */
export function ControlIcon({ name }: { name: ControlIconName }) {
  return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
    {name === "close" && <path d="m6 6 12 12M18 6 6 18" />}
    {name === "more" && <><circle cx="5" cy="12" r="1" /><circle cx="12" cy="12" r="1" /><circle cx="19" cy="12" r="1" /></>}
    {name === "options" && <><path d="M4 7h5m4 0h7M4 17h9m4 0h3" /><circle cx="11" cy="7" r="2" /><circle cx="15" cy="17" r="2" /></>}
    {name === "collapse" && <path d="m6 15 6-6 6 6" />}
    {name === "expand" && <path d="m6 9 6 6 6-6" />}
  </svg>;
}
