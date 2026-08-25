// andy-Card.sample.tsx — SAMPLE from a finished andy-theme deck (14 cards, production).
// Reference only: read for how a shell implements the canvas contract + anchors,
// then design your own shell for your theme. Not a copy-paste starting point.
// Note: --hs-orange / --hs-orange-soft are andy-local tokens (see references/themes.md).
import type { ReactNode } from "react";

type CardProps = {
  index: number;
  category: string;
  children: ReactNode;
  variant?: "default" | "cover";
};

export function Card({ index, category, children, variant = "default" }: CardProps) {
  const isCover = variant === "cover";
  return (
    <section
      data-card={index}
      aria-label={isCover ? "封面" : `卡片 ${index}`}
      style={{
        position: "relative",
        width: "1080px",
        height: "1440px",
        overflow: "hidden",
        background: "linear-gradient(160deg, var(--ra-color-bg) 0%, var(--ra-color-bg-tint) 100%)",
        color: "var(--ra-color-text)",
        fontFamily: "var(--ra-font-body)",
        borderRadius: "0",
        margin: "0 auto 32px auto",
        boxShadow: "var(--ra-shadow-lg)",
        isolation: "isolate",
      }}
    >
      {!isCover && (
        <header style={{
          position: "absolute", top: 0, left: 0, right: 0,
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "36px 56px 0 56px", zIndex: 2,
        }}>
          <PageBadge index={index} />
          <CategoryTag category={category} />
        </header>
      )}

      <div style={{
        position: "absolute", inset: 0,
        paddingTop: isCover ? "0" : "120px",
        paddingBottom: isCover ? "0" : "104px",
        paddingLeft: isCover ? "0" : "72px",
        paddingRight: isCover ? "0" : "72px",
        display: "flex", flexDirection: "column", zIndex: 1,
      }}>
        {children}
      </div>

      {!isCover && (
        <footer data-footer="true" style={{
          position: "absolute", bottom: 0, left: 0, right: 0,
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "0 64px 36px 64px",
          fontFamily: "var(--ra-font-heading)", fontSize: "24px", fontWeight: 600,
          color: "var(--ra-color-faint)", letterSpacing: "0.02em", zIndex: 2,
        }}>
          <span style={{ color: "var(--ra-color-muted)" }}>{/* brand line */}</span>
          <span>{index} / N</span>
        </footer>
      )}

      <span data-decor="true" aria-hidden="true" style={{
        position: "absolute", right: "-60px", bottom: "-60px",
        width: "180px", height: "180px", borderRadius: "999px",
        background: "var(--hs-orange)", opacity: 0.08, zIndex: 0, pointerEvents: "none",
      }} />
    </section>
  );
}

function PageBadge({ index }: { index: number }) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", justifyContent: "center",
      width: "68px", height: "68px", borderRadius: "999px",
      background: "var(--hs-orange)", color: "var(--ra-color-heading)",
      fontFamily: "var(--ra-font-heading)", fontWeight: 700, fontSize: "28px",
      boxShadow: "var(--ra-shadow-sm)",
    }}>{String(index).padStart(2, "0")}</span>
  );
}

function CategoryTag({ category }: { category: string }) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", padding: "12px 26px",
      borderRadius: "999px", background: "var(--hs-orange-soft)",
      color: "var(--ra-color-accent-strong)",
      fontFamily: "var(--ra-font-heading)", fontWeight: 700, fontSize: "26px",
    }}>{category}</span>
  );
}
