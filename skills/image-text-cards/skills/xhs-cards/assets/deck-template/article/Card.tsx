// Card — the shared shell. Only the canvas contract and audit anchors are fixed;
// design the header/footer/decor language yourself per theme (references/themes.md).
// Contract: 1080×1440 · overflow hidden · borderRadius 0 · data-card anchor.
import type { ReactNode } from "react";

export function Card({ index, variant = "content", children }: {
  index: number;
  variant?: "cover" | "content";
  children: ReactNode;
}) {
  const isCover = variant === "cover";
  return (
    <div
      data-card={index}
      style={{
        width: 1080,
        height: 1440,
        overflow: "hidden",
        borderRadius: 0,
        position: "relative",
        background: "var(--ra-color-bg)",
        fontFamily: "var(--ra-font-body)",
        color: "var(--ra-color-text)",
      }}
    >
      {/* content area: ≈1172px usable. Keep content off the bottom 118px (footer strip). */}
      <div style={{ position: "absolute", inset: 0, padding: isCover ? 0 : "150px 72px 118px 72px", display: "flex", flexDirection: "column" }}>
        {children}
      </div>
      {/* Add per-card: header (badge/tag), footer with data-footer="true",
          takeaway with data-takeaway="true", decor with data-decor="true".
          See references/card-anatomy.md — anchors are required by verify.mjs. */}
    </div>
  );
}
