import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { ThemeProvider } from "reacticle";
import "reacticle/styles.css";
import { Deck } from "./Deck";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider theme="__THEME__">
      <Deck />
    </ThemeProvider>
  </StrictMode>
);
