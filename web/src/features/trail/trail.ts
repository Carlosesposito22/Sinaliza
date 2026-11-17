// Regras de exibição da trilha (só front; não é ML). Funções puras para poder testar sem a interface.
// A trilha é feita de temas; cada tema tem aulas e uma prova. Quem decide o que abre é a API
// (GET /learn/progress); aqui só lemos esse estado.
import type { LessonStatus, PathResponse, Progress, Theme, ThemeStatus } from "../../contract";

// Aula sem entrada no progresso é tratada como bloqueada (nunca abrir por engano).
export function lessonStatus(progress: Progress | null, lessonId: string): LessonStatus {
  return progress?.lessons[lessonId]?.status ?? "locked";
}

export function themeStatus(progress: Progress | null, themeId: string): ThemeStatus {
  return progress?.themes[themeId]?.status ?? "locked";
}

// A prova abre com todas as aulas feitas; depois de aprovada, pode ser refeita para melhorar a nota.
export function examOpen(progress: Progress | null, themeId: string): boolean {
  const status = themeStatus(progress, themeId);
  return status === "exam_ready" || status === "passed";
}

export function stars(count: number): string {
  const n = Math.max(0, Math.min(3, count));
  return "★".repeat(n) + "☆".repeat(3 - n);
}

export function goalPercent(xpToday: number, goal: number): number {
  return goal > 0 ? Math.min(100, Math.round((xpToday / goal) * 100)) : 0;
}

export function percent(score: number): number {
  return Math.round(score * 100);
}

// Deslocamento horizontal de cada nó no caminho, em "passos" (-2 a 2), formando uma curva suave.
const WAVE = [0, 1, 2, 1, 0, -1, -2, -1];
export function nodeOffset(index: number): number {
  return WAVE[((index % WAVE.length) + WAVE.length) % WAVE.length];
}

export type Step = { kind: "lesson"; id: string } | { kind: "exam"; themeId: string };

// Onde a pessoa está: no primeiro tema aberto e ainda não aprovado, a prova (se já abriu) ou a
// primeira aula pendente. Null se não há nada pendente (tudo aprovado) ou faltam dados.
export function currentStep(path: PathResponse | null, progress: Progress | null): Step | null {
  if (!path || !progress) return null;
  for (const theme of path.themes) {
    const status = themeStatus(progress, theme.id);
    if (status === "locked" || status === "passed") continue;
    if (status === "exam_ready") return { kind: "exam", themeId: theme.id };
    const pending = theme.lessons.find((l) => lessonStatus(progress, l.id) === "available");
    if (pending) return { kind: "lesson", id: pending.id };
  }
  return null;
}

export interface ThemeSummary {
  status: ThemeStatus;
  completed: number;
  total: number;
  stars: number;
  attempts: number;
  bestScore: number;
  lastScore: number | null;
  mustRedo: boolean;
}

export function themeSummary(theme: Theme, progress: Progress | null): ThemeSummary {
  const tp = progress?.themes[theme.id];
  let starCount = 0;
  for (const lesson of theme.lessons) starCount += progress?.lessons[lesson.id]?.stars ?? 0;
  return {
    status: tp?.status ?? "locked",
    completed: tp?.lessons_completed ?? 0,
    total: tp?.lessons_total ?? theme.lessons.length,
    stars: starCount,
    attempts: tp?.exam_attempts ?? 0,
    bestScore: tp?.best_exam_score ?? 0,
    lastScore: tp?.last_exam_score ?? null,
    mustRedo: tp?.must_redo ?? false,
  };
}

export interface ProfileStats {
  lessonsCompleted: number;
  lessonsTotal: number;
  stars: number;
  maxStars: number;
  signsLearned: number;
  themesPassed: number;
  themesTotal: number;
}

// Números do perfil. "Sinais vistos" = sinais distintos das aulas já feitas alguma vez.
export function profileStats(path: PathResponse | null, progress: Progress | null): ProfileStats {
  const themes = path?.themes ?? [];
  let lessonsCompleted = 0;
  let lessonsTotal = 0;
  let starCount = 0;
  let themesPassed = 0;
  const signs = new Set<string>();
  for (const theme of themes) {
    if (themeStatus(progress, theme.id) === "passed") themesPassed += 1;
    for (const lesson of theme.lessons) {
      const lp = progress?.lessons[lesson.id];
      lessonsTotal += 1;
      starCount += lp?.stars ?? 0;
      if ((lp?.completions ?? 0) > 0) {
        lessonsCompleted += 1;
        lesson.glosses.forEach((g) => signs.add(g));
      }
    }
  }
  return {
    lessonsCompleted,
    lessonsTotal,
    stars: starCount,
    maxStars: lessonsTotal * 3,
    signsLearned: signs.size,
    themesPassed,
    themesTotal: themes.length,
  };
}

// Percentual do nível atual (0 a 100), a partir dos campos do progresso.
export function levelPercent(progress: Progress): number {
  const span = progress.xp_in_level + progress.xp_to_next_level;
  return span > 0 ? Math.round((progress.xp_in_level / span) * 100) : 0;
}
