import { describe, expect, it } from "vitest";
import type { PathResponse, Progress } from "../../contract";
import { nextAction } from "./home";

const lesson = (id: string, title: string) => ({ id, title, kind: "signs" as const, xp_reward: 20, n_exercises: 15, glosses: [] });
const path: PathResponse = {
  title: "Trilha",
  disclaimer: "",
  themes: [
    { id: "escola", title: "Escola", description: "", color: "#000", lessons: [lesson("e1", "A escola"), lesson("e2", "Estudar")],
      exam: { n_questions: 8, pass_score: 0.7, xp_reward: 50 } },
  ],
};
const lp = (status: string, completions = 0, needs_redo = false) => ({ status, stars: 0, best_accuracy: 0, completions, needs_redo });
const tp = (status: string) => ({ status, lessons_completed: 0, lessons_total: 2, exam_attempts: 0, best_exam_score: 0, last_exam_score: null, must_redo: false });
const progress = (lessons: Record<string, unknown>, theme = "learning", xp = 0) =>
  ({ xp, themes: { escola: tp(theme) }, lessons }) as unknown as Progress;

describe("nextAction", () => {
  it("convida a começar quem nunca fez aula", () => {
    expect(nextAction(path, progress({ e1: lp("available"), e2: lp("locked") }))).toEqual({
      to: "/licao/e1", label: "Começar a primeira aula", detail: "Escola · A escola",
    });
  });
  it("continua na próxima aula", () => {
    expect(nextAction(path, progress({ e1: lp("completed", 1), e2: lp("available") }, "learning", 20))).toMatchObject({
      to: "/licao/e2", label: "Continuar",
    });
  });
  it("manda refazer depois de reprovar", () => {
    expect(nextAction(path, progress({ e1: lp("available", 1, true), e2: lp("available", 1, true) }, "learning", 40)).label).toBe("Refazer aula");
  });
  it("leva à prova quando ela abriu", () => {
    expect(nextAction(path, progress({ e1: lp("completed", 1), e2: lp("completed", 1) }, "exam_ready", 40))).toEqual({
      to: "/prova/escola", label: "Fazer a prova", detail: "Tema Escola",
    });
  });
  it("sem dados ou tudo aprovado, vai para a trilha", () => {
    expect(nextAction(null, null).to).toBe("/trilha");
    expect(nextAction(path, progress({ e1: lp("completed", 1), e2: lp("completed", 1) }, "passed", 90)).detail).toMatch(/aprovado/);
  });
});
