// _shared — typography placeholders. The SIZES are floors (card-anatomy.md);
// the spacing/styling here is placeholder, not a house style — redesign per theme.
import type { ReactNode } from "react";

export function CardTitle({ children }: { children: ReactNode }) {
  return <h2 style={{ margin: "0 0 20px 0", fontFamily: "var(--ra-font-heading)", fontSize: 72, fontWeight: 700, color: "var(--ra-color-heading)", lineHeight: 1.12, letterSpacing: "-0.01em" }}>{children}</h2>;
}
export function CardLead({ children }: { children: ReactNode }) {
  return <p style={{ margin: "0 0 16px 0", fontFamily: "var(--ra-font-body)", fontSize: 30, lineHeight: 1.5, fontWeight: 600, color: "var(--ra-color-text)" }}>{children}</p>;
}
export function Body({ children }: { children: ReactNode }) {
  return <p style={{ margin: "0 0 16px 0", fontFamily: "var(--ra-font-body)", fontSize: 28, lineHeight: 1.55, color: "var(--ra-color-text)" }}>{children}</p>;
}
export function Takeaway({ children }: { children: ReactNode }) {
  return (
    <div data-takeaway="true" style={{ marginTop: "auto", padding: "26px 32px", borderRadius: 16, background: "var(--ra-color-accent)", color: "var(--ra-color-accent-contrast)", fontFamily: "var(--ra-font-heading)", fontSize: 28, fontWeight: 700, lineHeight: 1.42 }}>
      {children}
    </div>
  );
}
