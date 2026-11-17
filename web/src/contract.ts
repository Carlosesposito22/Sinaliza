// Tipos do contrato web ↔ API (versão 2). Espelham mock-api/sinaliza_mock/schemas.py e
// docs/contrato-api-web.md. Mudou um deles? Mude os três juntos e a versão do contrato.

export const CONTRACT_VERSION = "2";

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

// ---- Trilha de aprendizado (v2: temas → aulas → prova) ----
// Regra, não ML. Cada tema (escola, família...) tem aulas de sinais e de frases e termina numa prova:
// o avatar sinaliza sem legenda e a pessoa escreve o que entendeu. Nota >= pass_score libera o próximo
// tema; abaixo disso, ela refaz as aulas do tema antes de tentar de novo.

export type LessonKind = "signs" | "phrases";

export interface LessonSummary {
  id: string;
  title: string;
  kind: LessonKind;
  xp_reward: number;
  n_exercises: number;
  glosses: string[];
}

export interface ExamSummary {
  n_questions: number;
  pass_score: number; // 0 a 1
  xp_reward: number;
}

export interface Theme {
  id: string;
  title: string;
  description: string;
  color: string;
  lessons: LessonSummary[];
  exam: ExamSummary;
}

export interface PathResponse {
  title: string;
  // Mostre sempre em algum lugar da interface: os sinais não foram validados por falante de Libras.
  disclaimer: string;
  themes: Theme[];
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

// Frases: o avatar toca `glosses` em sequência, na ordem do português (não é a gramática da Libras).
export interface LearnPhraseExercise {
  id: string;
  type: "learn_phrase";
  glosses: string[];
  text: string;
}

export interface PhraseToTextExercise {
  id: string;
  type: "phrase_to_text";
  glosses: string[];
  options: { id: string; text: string }[];
  correct_option_id: string;
}

// Escrever o que o avatar sinalizou (como na prova). `text` é a resposta esperada: mostre só depois de
// verificar. A correção é da API (POST /learn/check), com a mesma regra da prova.
export interface SignToTextExercise {
  id: string;
  type: "sign_to_text";
  kind: "sign" | "phrase";
  glosses: string[];
  text: string;
}

export type Exercise =
  | LearnSignExercise
  | SignToWordExercise
  | WordToSignExercise
  | MatchPairsExercise
  | LearnPhraseExercise
  | PhraseToTextExercise
  | SignToTextExercise;

export interface Lesson {
  id: string;
  theme_id: string;
  title: string;
  kind: LessonKind;
  xp_reward: number;
  exercises: Exercise[];
}

export type LessonStatus = "locked" | "available" | "completed";

export interface LessonProgress {
  status: LessonStatus;
  stars: number; // 0 a 3
  best_accuracy: number; // 0 a 1
  completions: number;
  needs_redo: boolean; // reprovou na prova do tema: refazer esta aula
}

export type ThemeStatus = "locked" | "learning" | "exam_ready" | "passed";

export interface ThemeProgress {
  status: ThemeStatus;
  lessons_completed: number;
  lessons_total: number;
  exam_attempts: number;
  best_exam_score: number; // 0 a 1
  last_exam_score: number | null;
  must_redo: boolean; // reprovou na última prova e ainda não refez todas as aulas
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
  themes: Record<string, ThemeProgress>;
  lessons: Record<string, LessonProgress>;
  review_signs: number; // sinais errados esperando revisão
  challenge_available: boolean; // já há sinais vistos para o desafio do dia
  challenge_done_today: boolean;
}

// ---- Treino: escrever, revisão, desafio do dia, dicionário (regra, não ML; só os 210 sinais) ----

export interface CheckRequest {
  glosses: string[];
  text: string;
  answer: string;
}

export interface CheckResult {
  correct: boolean; // todos os sinais certos e nenhuma palavra sobrando
  score: number;
  expected_text: string;
  signs: SignCheck[];
  extra_words: string[];
}

export interface Practice {
  id: string; // sessão; conclua em POST /learn/practice/{id}/complete
  kind: "review" | "challenge";
  title: string;
  xp_reward: number;
  glosses: string[];
  exercises: Exercise[];
  completed_today: boolean;
}

export interface PracticeResult {
  passed: boolean;
  accuracy: number;
  xp_gained: number;
  level_up: boolean;
  goal_reached_now: boolean;
  cleared_glosses: string[];
  new_achievements: AchievementInfo[];
  progress: Progress;
}

export interface DictionaryEntry {
  gloss: string;
  word: string;
  forms: string[];
  theme_ids: string[]; // temas que ensinam o sinal (vazio: só no vocabulário)
  seen: boolean;
  mistakes: number;
}

export interface DictionaryResponse {
  total: number;
  seen_count: number;
  signs: DictionaryEntry[];
}

// ---- Conquistas (medalhas e troféus; regra, não ML) ----

export type AchievementKind = "medal" | "trophy";
export type AchievementTier = "bronze" | "silver" | "gold";
export type AchievementCategory = "provas" | "temas" | "aulas" | "habito";

export interface AchievementInfo {
  id: string;
  title: string;
  description: string;
  kind: AchievementKind;
  tier: AchievementTier;
  category: AchievementCategory;
  // exam, check, star, rocket, comeback, hand, book, flame, level, trophy, crown (desconhecido: desenho padrão)
  icon: string;
  unlocked: boolean;
  unlocked_at: string | null; // AAAA-MM-DD
  current: number; // limitado a target
  target: number;
}

export interface AchievementsResponse {
  unlocked_count: number;
  total: number;
  achievements: AchievementInfo[];
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
  exam_unlocked: boolean; // era a última aula que faltava: a prova do tema abriu
  new_achievements: AchievementInfo[]; // conquistas ganhas agora
  progress: Progress;
}

// ---- Prova do tema ----

export interface ExamQuestion {
  id: string;
  kind: "sign" | "phrase";
  glosses: string[]; // o avatar toca, sem legenda; a resposta certa não vem aqui
}

export interface Exam {
  theme_id: string;
  title: string;
  pass_score: number;
  questions: ExamQuestion[];
}

export interface ExamSubmit {
  answers: { question_id: string; text: string }[];
}

export interface SignCheck {
  gloss: string;
  word: string;
  correct: boolean;
}

export interface QuestionResult {
  question_id: string;
  kind: "sign" | "phrase";
  glosses: string[];
  expected_text: string;
  answer: string;
  score: number; // 0 a 1
  signs: SignCheck[];
  extra_words: string[];
}

export interface ExamResult {
  passed: boolean;
  score: number;
  pass_score: number;
  xp_gained: number;
  level_up: boolean;
  goal_reached_now: boolean;
  questions: QuestionResult[];
  unlocked_theme_ids: string[];
  must_redo_lesson_ids: string[];
  new_achievements: AchievementInfo[]; // conquistas ganhas agora
  progress: Progress;
}
