// 01-cover — starter placeholder. REPLACE with your designed cover
// (references/card-anatomy.md: split-screen, big anchor text, stat pills…).
import { Card } from "../Card";
import { CardTitle } from "./_shared";

export function Card01() {
  return (
    <Card index={1} variant="cover">
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%" }}>
        <CardTitle>deck title</CardTitle>
      </div>
    </Card>
  );
}
