// Deck — assembler: import every card, in order. One card per file under cards/.
import { Card01 } from "./cards/01-cover";

export function Deck() {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 40, padding: "40px 0" }}>
      <Card01 />
    </div>
  );
}
