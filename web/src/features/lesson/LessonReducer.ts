import type { KnownExercise } from "./exerciceTypes";

export type Phase = "answering" | "feedback" | "finished";

export interface LessonState {
  exercises: KnownExercise[];
  index: number;
  phase: Phase;
  correct: number;
  mistakes: string[]; // ids dos exercícios errados, como o POST /complete espera
  lastWasCorrect: boolean | null;
}

export type LessonAction =
  | { type: "answer"; correct: boolean } // exercícios com "Verificar"
  | { type: "acknowledge" } // learn_sign: conta como acerto e avança direto
  | { type: "next" }; // "Continuar" depois do feedback

export function initLesson(exercises: KnownExercise[]): LessonState {
  return {
    exercises,
    index: 0,
    phase: exercises.length === 0 ? "finished" : "answering",
    correct: 0,
    mistakes: [],
    lastWasCorrect: null,
  };
}

function advance(state: LessonState): LessonState {
  const last = state.index >= state.exercises.length - 1;
  return last
    ? { ...state, phase: "finished" }
    : { ...state, index: state.index + 1, phase: "answering", lastWasCorrect: null };
}

export function lessonReducer(state: LessonState, action: LessonAction): LessonState {
  const current = state.exercises[state.index];
  switch (action.type) {
    case "answer": {
      if (state.phase !== "answering" || !current) return state;
      return action.correct
        ? { ...state, phase: "feedback", correct: state.correct + 1, lastWasCorrect: true }
        : { ...state, phase: "feedback", mistakes: [...state.mistakes, current.id], lastWasCorrect: false };
    }
    case "acknowledge": {
      if (state.phase !== "answering" || current?.type !== "learn_sign") return state;
      return advance({ ...state, correct: state.correct + 1 });
    }
    case "next": {
      if (state.phase !== "feedback") return state;
      return advance(state);
    }
  }
}

/** Corpo do POST /learn/lessons/{id}/complete. */
export function toCompleteRequest(state: LessonState) {
  return { correct: state.correct, total: state.exercises.length, mistakes: state.mistakes };
}

/** Para a barra de progresso (0 a 1). Conta exercícios já respondidos. */
export function progressFraction(state: LessonState): number {
  if (state.exercises.length === 0) return 1;
  const done = state.phase === "finished" ? state.exercises.length : state.index + (state.phase === "feedback" ? 1 : 0);
  return done / state.exercises.length;
}