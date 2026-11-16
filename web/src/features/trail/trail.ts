// Regras de exibição da trilha (só front; não é ML). Funções puras para poder testar sem a interface.
import type { LessonStatus, PathResponse, Progress, Unit } from "../../contract";

// Lição sem entrada no progresso é tratada como bloqueada (nunca abrir por engano).
export function lessonStatus(progress: Progress | null, lessonId: string): LessonStatus {
  return progress?.lessons[lessonId]?.status ?? "locked";
}

export function stars(count: number): string {
  const n = Math.max(0, Math.min(3, count));
  return "★".repeat(n) + "☆".repeat(3 - n);
}

export function goalPercent(xpToday: number, goal: number): number {
  return goal > 0 ? Math.min(100, Math.round((xpToday / goal) * 100)) : 0;
}

// Deslocamento horizontal de cada nó no caminho, em "passos" (-2 a 2), formando uma curva suave.
const WAVE = [0, 1, 2, 1, 0, -1, -2, -1];
export function nodeOffset(index: number): number {
  return WAVE[((index % WAVE.length) + WAVE.length) % WAVE.length];
}

// A lição em que a pessoa está: a primeira disponível, na ordem da trilha. Null se não há nenhuma.
export function currentLessonId(path: PathResponse | null, progress: Progress | null): string | null {
  if (!path || !progress) return null;
  for (const unit of path.units) {
    for (const lesson of unit.lessons) {
      if (lessonStatus(progress, lesson.id) === "available") return lesson.id;
    }
  }
  return null;
}

export interface UnitSummary {
  completed: number;
  total: number;
  stars: number;
}

export function unitSummary(unit: Unit, progress: Progress | null): UnitSummary {
  let completed = 0;
  let starCount = 0;
  for (const lesson of unit.lessons) {
    const lp = progress?.lessons[lesson.id];
    if (lp?.status === "completed") completed += 1;
    starCount += lp?.stars ?? 0;
  }
  return { completed, total: unit.lessons.length, stars: starCount };
}

export interface ProfileStats {
  lessonsCompleted: number;
  lessonsTotal: number;
  stars: number;
  maxStars: number;
  signsLearned: number;
  unitsCompleted: number;
  unitsTotal: number;
}

// Números do perfil. "Sinais vistos" = sinais distintos das lições concluídas.
export function profileStats(path: PathResponse | null, progress: Progress | null): ProfileStats {
  const units = path?.units ?? [];
  let lessonsCompleted = 0;
  let lessonsTotal = 0;
  let starCount = 0;
  let unitsCompleted = 0;
  const signs = new Set<string>();
  for (const unit of units) {
    const s = unitSummary(unit, progress);
    lessonsCompleted += s.completed;
    lessonsTotal += s.total;
    starCount += s.stars;
    if (s.total > 0 && s.completed === s.total) unitsCompleted += 1;
    for (const lesson of unit.lessons) {
      if (lessonStatus(progress, lesson.id) === "completed") lesson.glosses.forEach((g) => signs.add(g));
    }
  }
  return {
    lessonsCompleted,
    lessonsTotal,
    stars: starCount,
    maxStars: lessonsTotal * 3,
    signsLearned: signs.size,
    unitsCompleted,
    unitsTotal: units.length,
  };
}

// Percentual do nível atual (0 a 100), a partir dos campos do progresso.
export function levelPercent(progress: Progress): number {
  const span = progress.xp_in_level + progress.xp_to_next_level;
  return span > 0 ? Math.round((progress.xp_in_level / span) * 100) : 0;
}
