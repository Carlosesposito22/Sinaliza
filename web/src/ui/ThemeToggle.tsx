// Botão para alternar entre o tema claro (padrão) e o escuro.
import { useState } from "react";
import { Moon, Sun } from "lucide-react";
import { applyTheme, savedTheme, type ThemeName } from "./theme";

export function ThemeToggle({ withLabel = false }: { withLabel?: boolean }) {
  const [theme, setTheme] = useState<ThemeName>(savedTheme);
  const next: ThemeName = theme === "dark" ? "light" : "dark";
  const label = next === "dark" ? "Usar tema escuro" : "Usar tema claro";
  return (
    <button
      type="button"
      className={withLabel ? "btn btn-secondary" : "btn btn-ghost btn-sm theme-toggle"}
      aria-label={label}
      title={label}
      onClick={() => {
        applyTheme(next);
        setTheme(next);
      }}
    >
      {next === "dark" ? <Moon aria-hidden="true" /> : <Sun aria-hidden="true" />}
      {withLabel && label}
    </button>
  );
}
