// Regras de exibição do dicionário (só front; não é ML). Os dados são os 210 sinais do vocabulário curado.
import type { DictionaryEntry } from "../../contract";

export type DictionaryFilter = "seen" | "all";

// "Mãe" → "mae": a busca ignora acento e maiúscula.
export function fold(text: string): string {
  return text.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();
}

// Filtra por "meus sinais"/"todos" e pela busca (na palavra e nas outras formas aceitas).
export function filterDictionary(signs: DictionaryEntry[], filter: DictionaryFilter, query: string): DictionaryEntry[] {
  const q = fold(query);
  return signs.filter(
    (s) => (filter === "all" || s.seen) && (!q || [s.word, ...s.forms].some((form) => fold(form).includes(q))),
  );
}

// Primeira letra (sem acento) para agrupar a lista: "Água" fica em "A".
export function initial(word: string): string {
  return fold(word).charAt(0).toUpperCase() || "#";
}
