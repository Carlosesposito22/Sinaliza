import React from "react";
import ReactDOM from "react-dom/client";
import { HashRouter } from "react-router-dom";
import { App } from "./app/App";
import "./ui/tokens.css";
import "./ui/components.css";
import { applyTheme, savedTheme } from "./ui/theme";

// Tema antes de desenhar a primeira tela (evita piscar claro → escuro).
applyTheme(savedTheme());

// HashRouter: as rotas funcionam no nginx do Docker sem configuração extra de fallback.
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <HashRouter>
      <App />
    </HashRouter>
  </React.StrictMode>,
);
