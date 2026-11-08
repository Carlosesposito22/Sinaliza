import type { LessonStatus, Progress } from "../../contract";

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
