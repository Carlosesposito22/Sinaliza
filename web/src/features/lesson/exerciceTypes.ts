// TODO: trocar estas definições por imports de '../../contract' e apagar o que sobrar aqui.

export interface LearnSign { id: string; type: "learn_sign"; gloss: string; word_pt: string; forms: string[] }
export interface SignToWord { id: string; type: "sign_to_word"; gloss: string; options: { id: string; text: string }[]; correct_option_id: string }
export interface WordToSign { id: string; type: "word_to_sign"; text: string; options: { id: string; gloss: string }[]; correct_option_id: string }
export interface MatchPairs { id: string; type: "match_pairs"; pairs: { id: string; gloss: string; text: string }[] }

export type KnownExercise = LearnSign | SignToWord | WordToSign | MatchPairs;
// A API pode ganhar tipos novos: o front precisa sobreviver a eles.
export type Exercise = KnownExercise | { id: string; type: string; [k: string]: unknown };

const KNOWN = new Set(["learn_sign", "sign_to_word", "word_to_sign", "match_pairs"]);

export function isKnownExercise(e: Exercise): e is KnownExercise {
  return KNOWN.has(e.type);
}

/** Descarta tipos desconhecidos antes de começar, para que `total` bata com o que a pessoa realmente jogou. */
export function playableExercises(exercises: Exercise[]): KnownExercise[] {
  return exercises.filter(isKnownExercise);
}