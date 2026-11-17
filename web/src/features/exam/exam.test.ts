import { describe, expect, it } from "vitest";
import type { Exam, ExamResult, QuestionResult } from "../../contract";
import { answeredCount, questionLabel, resultHeadline, reviewOrder, toSubmit, verdict } from "./exam";

const exam: Exam = {
  theme_id: "escola",
  title: "Prova: Escola",
  pass_score: 0.7,
  questions: [
    { id: "q1", kind: "sign", glosses: ["ALUNO"] },
    { id: "q2", kind: "phrase", glosses: ["PROFESSOR", "PODER", "IR", "BANHEIRO"] },
  ],
};

const q = (id: string, score: number) => ({ question_id: id, score }) as QuestionResult;

describe("exam", () => {
  it("envia todas as questões, com as em branco vazias e sem espaços sobrando", () => {
    expect(toSubmit(exam, { q2: "  professora posso ir ao banheiro " })).toEqual({
      answers: [
        { question_id: "q1", text: "" },
        { question_id: "q2", text: "professora posso ir ao banheiro" },
      ],
    });
  });
  it("conta só as respondidas", () => {
    expect(answeredCount(exam, { q1: "aluno", q2: "   " })).toBe(1);
  });
  it("rotula sinal e frase", () => {
    expect(questionLabel("sign", 1)).toBe("Que sinal é este?");
    expect(questionLabel("phrase", 4)).toBe("Que frase é esta? (4 sinais)");
  });
  it("classifica o acerto e põe as erradas primeiro", () => {
    expect([verdict(q("a", 1)), verdict(q("b", 0.5)), verdict(q("c", 0))]).toEqual(["right", "partial", "wrong"]);
    expect(reviewOrder([q("a", 1), q("b", 0), q("c", 0.5)]).map((x) => x.question_id)).toEqual(["b", "c", "a"]);
  });
  it("escreve o título do resultado", () => {
    const base = { unlocked_theme_ids: [] } as unknown as ExamResult;
    expect(resultHeadline({ ...base, passed: true, unlocked_theme_ids: ["familia"] })).toMatch(/liberado/);
    expect(resultHeadline({ ...base, passed: true })).toBe("Aprovado!");
    expect(resultHeadline({ ...base, passed: false })).toMatch(/Ainda não/);
  });
});
