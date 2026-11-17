// Tema claro (padrão, branco e azul) ou escuro, escolhido pela pessoa e guardado só neste navegador.
// Só front; não é ML.
export type ThemeName = "light" | "dark";

const KEY = "sinaliza.theme";

export function savedTheme(): ThemeName {
  try {
    return localStorage.getItem(KEY) === "dark" ? "dark" : "light";
  } catch {
    return "light"; // sem localStorage: fica o claro
  }
}

export function applyTheme(theme: ThemeName): void {
  document.documentElement.dataset.theme = theme;
  try {
    localStorage.setItem(KEY, theme);
  } catch {
    // sem localStorage: vale só nesta visita
  }
}
