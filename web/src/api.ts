export interface PoseSequence {
  fps: number;
  layout: Record<string, [number, number]>;
  frames: number[][][];
}

// exact: está na tabela. approx: aproximada por embedding (proposta). function: artigo ou
// preposição, sem sinal próprio. ignored: sem sinal no vocabulário.
export type MatchKind = "exact" | "approx" | "function" | "ignored";

export interface WordMatch {
  word: string;
  gloss: string | null;
  kind: MatchKind;
  score: number;
}

export interface TranslateResponse {
  text: string;
  glosses: string[];
  matches: WordMatch[];
  // "playback": gravações reais tocadas em sequência; "stub": aceno de teste, não corresponde aos sinais.
  generator: string;
  pose: PoseSequence;
}

export interface Phrase {
  text: string;
  glosses: string[];
  ignored: string[];
}

export interface Category {
  id: string;
  label: string;
  phrases: Phrase[];
}

export interface SignInfo {
  gloss: string;
  forms: string[];
  contexts: string[];
  note: string | null;
}

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function translate(text: string): Promise<TranslateResponse> {
  const response = await fetch(`${API_URL}/translate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!response.ok) {
    throw new Error(await errorMessage(response));
  }
  return response.json();
}

export async function fetchCategories(): Promise<Category[]> {
  const response = await fetch(`${API_URL}/categories`);
  if (!response.ok) {
    throw new Error(`A API respondeu ${response.status}`);
  }
  return (await response.json()).categories;
}

export async function fetchVocabulary(): Promise<SignInfo[]> {
  const response = await fetch(`${API_URL}/vocabulary`);
  if (!response.ok) {
    throw new Error(`A API respondeu ${response.status}`);
  }
  return (await response.json()).signs;
}

// A API devolve `detail` como texto nos erros que ela mesma gera (ex.: 422 sem sinais).
async function errorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") {
      return body.detail;
    }
  } catch {
    // corpo sem JSON: cai na mensagem genérica
  }
  return `A API respondeu ${response.status}`;
}
