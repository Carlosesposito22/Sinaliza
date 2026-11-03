// Tipos do contrato web ↔ API (versão 1). Espelham mock-api/sinaliza_mock/schemas.py e
// docs/contrato-api-web.md. Mudou um deles? Mude os três juntos e a versão do contrato.

export const CONTRACT_VERSION = "1";

// ---- Tradutor (ML) ----

export type MatchKind = "exact" | "approx" | "function" | "ignored";
export type Decision = "MANTER" | "DESCARTAR";

export interface WordMatch {
  word: string;
  gloss: string | null;
  kind: MatchKind;
  score: number;
  // O que o modelo de ML decidiu para a palavra e com que probabilidade de MANTER (0 a 1).
  decision: Decision;
  probability: number;
}

export interface TranslateResponse {
  text: string;
  glosses: string[];
  matches: WordMatch[];
  generator: string;
  // Legado: o avatar do VLibras toca `glosses`; não dependa de `pose`.
  pose: unknown | null;
  // "sinaliza-t1/1", "lista-fixa" ou "mock".
  model_version: string;
  latency_ms: number;
}

// ---- Trilha de aprendizado ----

export interface LessonSummary {
  id: string;
  title: string;
  xp_reward: number;
  n_exercises: number;
  glosses: string[];
}

export interface Unit {
  id: string;
  title: string;
  description: string;
  color: string;
  icon: string;
  lessons: LessonSummary[];
}

export interface PathResponse {
  title: string;
  // Mostre sempre em algum lugar da interface: os sinais não foram validados por falante de Libras.
  disclaimer: string;
  units: Unit[];
}

export interface LearnSignExercise {
  id: string;
  type: "learn_sign";
  gloss: string;
  word_pt: string;
  forms: string[];
}

export interface SignToWordExercise {
  id: string;
  type: "sign_to_word";
  gloss: string;
  options: { id: string; text: string }[];
  correct_option_id: string;
}

export interface WordToSignExercise {
  id: string;
  type: "word_to_sign";
  text: string;
  options: { id: string; gloss: string }[];
  correct_option_id: string;
}

export interface MatchPairsExercise {
  id: string;
  type: "match_pairs";
  pairs: { id: string; gloss: string; text: string }[];
}

export type Exercise = LearnSignExercise | SignToWordExercise | WordToSignExercise | MatchPairsExercise;

export interface Lesson {
  id: string;
  unit_id: string;
  title: string;
  xp_reward: number;
  exercises: Exercise[];
}

export type LessonStatus = "locked" | "available" | "completed";

export interface LessonProgress {
  status: LessonStatus;
  stars: number; // 0 a 3
  best_accuracy: number; // 0 a 1
  completions: number;
}

export interface Progress {
  learner_id: string;
  xp: number;
  level: number;
  xp_in_level: number;
  xp_to_next_level: number;
  streak_days: number;
  best_streak: number;
  daily_goal_xp: number;
  xp_today: number;
  goal_reached_today: boolean;
  last_activity_date: string | null; // AAAA-MM-DD
  lessons: Record<string, LessonProgress>;
}

export interface CompleteRequest {
  correct: number;
  total: number;
  mistakes: string[]; // ids dos exercícios errados
}

export interface LessonResult {
  passed: boolean;
  accuracy: number;
  stars: number;
  xp_gained: number;
  bonus_perfect: boolean;
  level_up: boolean;
  goal_reached_now: boolean;
  unlocked_lesson_ids: string[];
  progress: Progress;
}
