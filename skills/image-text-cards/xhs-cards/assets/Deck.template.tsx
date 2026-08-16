// Deck.template.tsx — copy to article/Deck.tsx. Assembler: import + order N cards.
// One card per file under article/cards/NN-*.tsx. See references/card-anatomy.md.
import { Card } from "./Card";
import { Card01Cover } from "./cards/01-cover";
// import { Card02Overview } from "./cards/02-overview";
// … one import per card …

export function Deck() {
  return (
    <>
      <Card index={1} category="封面" variant="cover">
        <Card01Cover />
      </Card>
      {/* <Card index={2} category="总览"><Card02Overview /></Card> */}
      {/* … one Card wrapper per card, in order … */}
    </>
  );
}
