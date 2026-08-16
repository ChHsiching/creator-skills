// shared.template.tsx — copy to article/cards/_shared.tsx.
// Font sizes are the floor (pitfall 3). Icon is SVG, never emoji (pitfall 1).
// See references/card-anatomy.md.
import type { CSSProperties, ReactNode } from "react";

// ── Icon · SVG line icons (Feather-like). Never emoji. ──
const ICON_PATHS: Record<string, ReactNode> = {
  plug: (<><path d="M9 7V3M15 7V3M7 7h10v5a5 5 0 0 1-10 0V7zM12 17v4" /></>),
  puzzle: (<><path d="M8 4h3a1 1 0 0 1 1 1 1.5 1.5 0 0 0 3 0 1 1 0 0 1 1-1h3v3a1 1 0 0 0 0 2v3a1 1 0 0 1-1 1h-3a1.5 1.5 0 0 0-3 0 1 1 0 0 1-1 1H8v-4a1.5 1.5 0 0 0-2 0 1 1 0 0 1-1 1V4z" /></>),
  book: (<><path d="M4 5a2 2 0 0 1 2-2h12v16H6a2 2 0 0 0-2 2zM18 3v18" /><path d="M8 7h6M8 11h6" /></>),
  edit: (<><path d="M4 20h4L18 10l-4-4L4 16zM14 6l4 4" /></>),
  target: (<><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="4" /><circle cx="12" cy="12" r="0.6" fill="currentColor" stroke="none" /></>),
  wand: (<><path d="M5 19L16 8M14 6l4 4M9 4l1 2 2 1-2 1-1 2-1-2-2-1 2-1zM18 14l.6 1.4L20 16l-1.4.6L18 18l-.6-1.4L16 16l1.4-.6z" /></>),
  clipboard: (<><rect x="6" y="4" width="12" height="17" rx="2" /><path d="M9 4a3 3 0 0 1 6 0M9 11h6M9 15h4" /></>),
  tree: (<><path d="M12 22V8M12 8a4 4 0 1 0-4-4M12 8a4 4 0 1 1 4-4M8 12H5a3 3 0 0 1 0-6M16 12h3a3 3 0 0 0 0-6" /></>),
  folder: (<><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /></>),
  compass: (<><circle cx="12" cy="12" r="9" /><path d="M15.5 8.5l-2 5-5 2 2-5z" /></>),
  broom: (<><path d="M14 4l6 6M16 6l-9 9c-2 2-4 1-5 3 2 1 5 1 7-1l4-4M7 18l3 3" /></>),
  bulb: (<><path d="M9 18h6M10 22h4M12 2a7 7 0 0 0-4 12.7c.6.5 1 1.3 1 2.1V18h6v-1.2c0-.8.4-1.6 1-2.1A7 7 0 0 0 12 2z" /></>),
  check: (<><path d="M5 12l5 5 9-10" /></>),
  x: (<><path d="M6 6l12 12M18 6L6 18" /></>),
};

export function Icon({ name, size = 32, strokeWidth = 2.4 }: { name: string; size?: number; strokeWidth?: number }) {
  const path = ICON_PATHS[name] ?? ICON_PATHS.bulb;
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"
      style={{ flexShrink: 0, display: "block" }}>
      {path}
    </svg>
  );
}

export function CardTitle({ children }: { children: ReactNode }) {
  return <h2 style={{ margin: "0 0 18px 0", fontFamily: "var(--ra-font-heading)", fontSize: "72px", fontWeight: 800, color: "var(--ra-color-heading)", lineHeight: 1.08, letterSpacing: "-0.01em" }}>{children}</h2>;
}
export function CardTitleSm({ children }: { children: ReactNode }) {
  return <h2 style={{ margin: "0 0 16px 0", fontFamily: "var(--ra-font-heading)", fontSize: "58px", fontWeight: 800, color: "var(--ra-color-heading)", lineHeight: 1.1, letterSpacing: "-0.01em" }}>{children}</h2>;
}
export function CardLead({ children }: { children: ReactNode }) {
  return <p style={{ margin: "0 0 14px 0", fontFamily: "var(--ra-font-body)", fontSize: "30px", lineHeight: 1.5, color: "var(--ra-color-text)", fontWeight: 600 }}>{children}</p>;
}
export function Body({ children, style }: { children: ReactNode; style?: CSSProperties }) {
  return <p style={{ margin: "0 0 16px 0", fontFamily: "var(--ra-font-body)", fontSize: "28px", lineHeight: 1.55, color: "var(--ra-color-text)", ...style }}>{children}</p>;
}
export function Takeaway({ children, icon = "bulb" }: { children: ReactNode; icon?: string }) {
  return (
    <div style={{ marginTop: "auto", padding: "26px 32px", borderRadius: "var(--ra-radius-lg)", background: "var(--hs-orange)", color: "var(--ra-color-heading)", fontFamily: "var(--ra-font-heading)", fontSize: "28px", fontWeight: 700, lineHeight: 1.4, boxShadow: "var(--ra-shadow-md)", display: "flex", alignItems: "center", gap: "18px" }}>
      <Icon name={icon} size={34} />
      <span>{children}</span>
    </div>
  );
}
export function Code({ children }: { children: ReactNode }) {
  return <code style={{ fontFamily: "var(--ra-font-mono)", fontSize: "0.86em", background: "var(--ra-color-surface-2)", color: "var(--ra-color-accent-strong)", padding: "3px 12px", borderRadius: "var(--ra-radius-sm)", fontWeight: 600 }}>{children}</code>;
}
export function SoftRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "20px", padding: "20px 26px", borderRadius: "var(--ra-radius-md)", background: "var(--ra-color-surface)", boxShadow: "var(--ra-shadow-sm)" }}>
      <span style={{ fontFamily: "var(--ra-font-heading)", fontSize: "26px", fontWeight: 700, color: "var(--ra-color-accent-strong)", whiteSpace: "nowrap", minWidth: "fit-content" }}>{label}</span>
      <span style={{ fontFamily: "var(--ra-font-body)", fontSize: "26px", color: "var(--ra-color-text)", lineHeight: 1.4 }}>{children}</span>
    </div>
  );
}
export function BlockLabel({ children }: { children: ReactNode }) {
  return (
    <div style={{ fontFamily: "var(--ra-font-heading)", fontSize: "26px", fontWeight: 700, color: "var(--ra-color-muted)", letterSpacing: "0.04em", margin: "10px 0 14px 0", display: "flex", alignItems: "center", gap: "14px" }}>
      <span style={{ width: "32px", height: "5px", borderRadius: "999px", background: "var(--hs-orange)", display: "inline-block" }} />
      {children}
    </div>
  );
}
