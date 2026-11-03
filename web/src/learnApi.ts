// Cliente da trilha de aprendizado. Funciona igual contra o mock e contra a API real: só muda
// VITE_API_URL (padrão http://localhost:8000). Ver docs/contrato-api-web.md.
import type { CompleteRequest, Lesson, LessonResult, PathResponse, Progress } from "./contract";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const LEARNER_KEY = "sinaliza.learnerId";

// Perfil anônimo: o front gera um UUID uma vez e o manda em todas as chamadas de progresso.
export function learnerId(): string {
  try {
    let id = localStorage.getItem(LEARNER_KEY);
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem(LEARNER_KEY, id);
    }
    return id;
  } catch {
    return "anonimo"; // localStorage indisponível (modo privado): progresso compartilhado e volátil
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", "X-Learner-Id": learnerId(), ...init.headers },
  });
  if (!response.ok) {
    let message = `A API respondeu ${response.status}`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") message = body.detail;
    } catch {
      // corpo sem JSON: fica a mensagem genérica
    }
    throw new Error(message);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export const fetchPath = () => request<PathResponse>("/learn/path");
export const fetchLesson = (id: string) => request<Lesson>(`/learn/lessons/${encodeURIComponent(id)}`);
export const fetchProgress = () => request<Progress>("/learn/progress");
export const completeLesson = (id: string, body: CompleteRequest) =>
  request<LessonResult>(`/learn/lessons/${encodeURIComponent(id)}/complete`, {
    method: "POST",
    body: JSON.stringify(body),
  });
// Só existe no mock.
export const resetProgress = () => request<void>("/learn/progress", { method: "DELETE" });
