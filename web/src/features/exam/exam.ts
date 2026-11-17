// Regras da tela da prova (só front; não é ML). A correção de verdade é da API (POST /learn/themes/{id}/exam);
// aqui só montamos o envio e os textos do resultado.
import type { Exam, ExamResult, ExamSubmit, QuestionResult } from "../../contract";

// Toda questão vai no envio; a que ficou em branco vale 0 na correção.
export function toSubmit(exam: Exam, answers: Record<string, string>): ExamSubmit {
  return { answers: exam.questions.map((q) => ({ question_id: q.id, text: (answers[q.id] ?? "").trim() })) };
}

export function answeredCount(exam: Exam, answers: Record<string, string>): number {
  return exam.questions.filter((q) => (answers[q.id] ?? "").trim() !== "").length;
}

export function questionLabel(kind: "sign" | "phrase", nSigns: number): string {
  return kind === "sign" ? "Que sinal é este?" : `Que frase é esta? (${nSigns} sinais)`;
}

export type Verdict = "right" | "partial" | "wrong";

export function verdict(q: QuestionResult): Verdict {
  if (q.score >= 1) return "right";
  return q.score > 0 ? "partial" : "wrong";
}

// Questões erradas primeiro: é o que a pessoa precisa rever.
export function reviewOrder(questions: QuestionResult[]): QuestionResult[] {
  return [...questions].sort((a, b) => a.score - b.score);
}

export function resultHeadline(result: ExamResult): string {
  if (result.passed) return result.unlocked_theme_ids.length > 0 ? "Aprovado! Próximo tema liberado." : "Aprovado!";
  return "Ainda não foi desta vez.";
}
