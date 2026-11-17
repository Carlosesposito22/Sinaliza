import { describe, expect, it } from "vitest";
import type { PathResponse, Progress, ThemeProgress } from "../../contract";
import {
  currentStep,
  examOpen,
  goalPercent,
  lessonStatus,
  levelPercent,
  nodeOffset,
  percent,
  profileStats,
  stars,
  themeStatus,
  themeSummary,
} from "./trail";

const lp = (status: string, stars = 0, completions = 0) => ({ status, stars, best_accuracy: 0, completions, needs_redo: false });
const tp = (status: string, extra: Partial<ThemeProgress> = {}) => ({
  status, lessons_completed: 0, lessons_total: 2, exam_attempts: 0, best_exam_score: 0, last_exam_score: null, must_redo: false, ...extra,
});

const progress = {
  xp: 130,
  xp_in_level: 30,
  xp_to_next_level: 70,
  themes: { t1: tp("learning", { lessons_completed: 1 }), t2: tp("locked", { lessons_total: 1 }) },
  lessons: { a: lp("completed", 3, 1), b: lp("available"), c: lp("locked") },
} as unknown as Progress;

const lesson = (id: string, glosses: string[]) => ({ id, title: id, kind: "signs" as const, xp_reward: 20, n_exercises: 13, glosses });
const exam = { n_questions: 3, pass_score: 0.7, xp_reward: 50 };
const path: PathResponse = {
  title: "Trilha",
  disclaimer: "aviso",
  themes: [
    { id: "t1", title: "T1", description: "", color: "#fff", lessons: [lesson("a", ["MÃE", "PAI"]), lesson("b", ["PAI", "FILHO"])], exam },
    { id: "t2", title: "T2", description: "", color: "#fff", lessons: [lesson("c", ["CASA"])], exam },
  ],
};

describe("trail", () => {
  it("lê o estado da aula e do tema e bloqueia o desconhecido", () => {
    expect(lessonStatus(progress, "a")).toBe("completed");
    expect(lessonStatus(progress, "b")).toBe("available");
    expect(lessonStatus(progress, "x")).toBe("locked");
    expect(lessonStatus(null, "a")).toBe("locked");
    expect(themeStatus(progress, "t1")).toBe("learning");
    expect(themeStatus(progress, "zz")).toBe("locked");
  });
  it("só abre a prova com as aulas feitas ou o tema aprovado", () => {
    expect(examOpen(progress, "t1")).toBe(false);
    const ready = { ...progress, themes: { ...progress.themes, t1: tp("exam_ready") } } as Progress;
    expect(examOpen(ready, "t1")).toBe(true);
    const passed = { ...progress, themes: { ...progress.themes, t1: tp("passed") } } as Progress;
    expect(examOpen(passed, "t1")).toBe(true);
  });
  it("desenha estrelas limitadas a 0–3", () => {
    expect(stars(2)).toBe("★★☆");
    expect(stars(9)).toBe("★★★");
    expect(stars(-1)).toBe("☆☆☆");
  });
  it("calcula percentuais", () => {
    expect(goalPercent(10, 20)).toBe(50);
    expect(goalPercent(45, 20)).toBe(100);
    expect(goalPercent(5, 0)).toBe(0);
    expect(percent(0.6875)).toBe(69);
  });
  it("desloca os nós em curva e repete o padrão", () => {
    expect([0, 1, 2, 3, 4, 5, 6, 7].map(nodeOffset)).toEqual([0, 1, 2, 1, 0, -1, -2, -1]);
    expect(nodeOffset(8)).toBe(0);
  });
  it("acha o passo atual: a aula pendente, depois a prova, depois o próximo tema", () => {
    expect(currentStep(path, progress)).toEqual({ kind: "lesson", id: "b" });
    expect(currentStep(null, progress)).toBeNull();
    const ready = { ...progress, themes: { ...progress.themes, t1: tp("exam_ready") } } as Progress;
    expect(currentStep(path, ready)).toEqual({ kind: "exam", themeId: "t1" });
    const next = {
      ...progress,
      themes: { t1: tp("passed"), t2: tp("learning") },
      lessons: { ...progress.lessons, c: lp("available") },
    } as unknown as Progress;
    expect(currentStep(path, next)).toEqual({ kind: "lesson", id: "c" });
    const done = { ...progress, themes: { t1: tp("passed"), t2: tp("passed") } } as unknown as Progress;
    expect(currentStep(path, done)).toBeNull();
  });
  it("resume um tema", () => {
    expect(themeSummary(path.themes[0], progress)).toMatchObject({ status: "learning", completed: 1, total: 2, stars: 3 });
    expect(themeSummary(path.themes[1], null)).toMatchObject({ status: "locked", completed: 0, total: 1, stars: 0 });
  });
  it("calcula os números do perfil (sinais distintos só das aulas feitas)", () => {
    expect(profileStats(path, progress)).toEqual({
      lessonsCompleted: 1,
      lessonsTotal: 3,
      stars: 3,
      maxStars: 9,
      signsLearned: 2,
      themesPassed: 0,
      themesTotal: 2,
    });
  });
  it("calcula o percentual do nível", () => {
    expect(levelPercent(progress)).toBe(30);
  });
});
