// Regras da página inicial (só front; não é ML): para onde o botão "continuar" leva e o que ele diz.
import type { PathResponse, Progress } from "../../contract";
import { currentStep } from "../trail/trail";

export interface NextAction {
  to: string;
  label: string;
  detail: string | null; // tema e passo, em letra menor
}

export function nextAction(path: PathResponse | null, progress: Progress | null): NextAction {
  const step = currentStep(path, progress);
  if (!path || !progress || !step) {
    return { to: "/trilha", label: "Ver a trilha", detail: progress && path ? "Tudo aprovado por enquanto!" : null };
  }
  const started = progress.xp > 0 || Object.values(progress.lessons).some((l) => l.completions > 0);
  if (step.kind === "exam") {
    const theme = path.themes.find((t) => t.id === step.themeId);
    return { to: `/prova/${step.themeId}`, label: "Fazer a prova", detail: theme ? `Tema ${theme.title}` : null };
  }
  for (const theme of path.themes) {
    const lesson = theme.lessons.find((l) => l.id === step.id);
    if (lesson) {
      const redo = progress.lessons[lesson.id]?.needs_redo ?? false;
      return {
        to: `/licao/${lesson.id}`,
        label: redo ? "Refazer aula" : started ? "Continuar" : "Começar a primeira aula",
        detail: `${theme.title} · ${lesson.title}`,
      };
    }
  }
  return { to: "/trilha", label: "Ver a trilha", detail: null };
}
