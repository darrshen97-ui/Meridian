import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";
import { initTheme } from "./theme";

initTheme();

// The script ran, so the "didn't finish loading" notice is no longer true.
document.getElementById("boot-fallback")?.remove();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
