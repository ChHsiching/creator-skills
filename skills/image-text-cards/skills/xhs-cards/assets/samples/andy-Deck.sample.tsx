// andy-Deck.sample.tsx — SAMPLE from a finished andy-theme deck. Reference only.
import { Card } from "./Card";
import { Card01Cover } from "./cards/01-cover";

export function Deck() {
  return (
    <>
      <Card index={1} category="封面" variant="cover">
        <Card01Cover />
      </Card>
    </>
  );
}
