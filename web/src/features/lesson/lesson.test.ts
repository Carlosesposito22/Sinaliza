import { describe, expect, it } from "vitest";
import type { Exercise, KnownExercise } from "./exerciceTypes";
import { playableExercises } from "./exerciceTypes";
import { gradeChoice, gradeMatchPairs, isPairMatch } from "./grading";
import { initLesson, lessonReducer, progressFraction, toCompleteRequest } from "./LessonReducer";
import type { LessonAction, LessonState } from "./LessonReducer"

const learn: KnownExercise = { id: "e1", type: "learn_sign", gloss: "FAMÍLIA", word_pt: "família", forms: ["família"] };
const s2w: KnownExercise = {
  id: "e2", type: "sign_to_word", gloss: "FAMÍLIA",
  options: [{ id: "a", text: "menina" }, { id: "b", text: "família" }], correct_option_id: "b",
};
const w2s: KnownExercise = {
  id: "e3", type: "word_to_sign", text: "família",
  options: [{ id: "a", gloss: "AMIGO" }, { id: "b", gloss: "FAMÍLIA" }], correct_option_id: "b",
};

const run = (s: LessonState, ...actions: LessonAction[]) => actions.reduce(lessonReducer, s);

describe("grading", () => {
  it("corrige escolha por id", () => {
    expect(gradeChoice(s2w as never, "b")).toBe(true);
    expect(gradeChoice(w2s as never, "a")).toBe(false);
  });
  it("par só combina com o mesmo id", () => {
    expect(isPairMatch("p1", "p1")).toBe(true);
    expect(isPairMatch("p1", "p2")).toBe(false);
  });
  it("match_pairs só acerta sem tentativas erradas", () => {
    expect(gradeMatchPairs(0)).toBe(true);
    expect(gradeMatchPairs(1)).toBe(false);
  });
});

describe("playableExercises", () => {
  it("ignora tipos desconhecidos sem quebrar", () => {
    const mixed: Exercise[] = [learn, { id: "x", type: "futuro" }, s2w];
    expect(playableExercises(mixed).map((e) => e.id)).toEqual(["e1", "e2"]);
  });
});

describe("lessonReducer", () => {
  it("learn_sign conta como acerto e avança direto", () => {
    const s = run(initLesson([learn, s2w]), { type: "acknowledge" });
    expect(s).toMatchObject({ index: 1, correct: 1, phase: "answering" });
  });

  it("acknowledge é ignorado em exercício que não é learn_sign", () => {
    const s0 = initLesson([s2w]);
    expect(run(s0, { type: "acknowledge" })).toBe(s0);
  });

  it("erro registra o id e vai para feedback", () => {
    const s = run(initLesson([s2w, w2s]), { type: "answer", correct: false });
    expect(s).toMatchObject({ phase: "feedback", correct: 0, mistakes: ["e2"], lastWasCorrect: false });
  });

  it("não aceita duas respostas no mesmo exercício", () => {
    const s = run(initLesson([s2w, w2s]), { type: "answer", correct: true }, { type: "answer", correct: true });
    expect(s.correct).toBe(1);
  });

  it("'next' só funciona depois do feedback", () => {
    const s0 = initLesson([s2w, w2s]);
    expect(run(s0, { type: "next" })).toBe(s0);
  });

  it("fluxo completo gera o corpo do /complete", () => {
    const s = run(
      initLesson([learn, s2w, w2s]),
      { type: "acknowledge" },
      { type: "answer", correct: true }, { type: "next" },
      { type: "answer", correct: false }, { type: "next" },
    );
    expect(s.phase).toBe("finished");
    expect(toCompleteRequest(s)).toEqual({ correct: 2, total: 3, mistakes: ["e3"] });
  });

  it("lição vazia já nasce finalizada", () => {
    expect(initLesson([]).phase).toBe("finished");
  });

  it("barra de progresso avança com o feedback e fecha em 1", () => {
    let s = initLesson([s2w, w2s]);
    expect(progressFraction(s)).toBe(0);
    s = run(s, { type: "answer", correct: true });
    expect(progressFraction(s)).toBe(0.5);
    s = run(s, { type: "next" }, { type: "answer", correct: true }, { type: "next" });
    expect(progressFraction(s)).toBe(1);
  });
});