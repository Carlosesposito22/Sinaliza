// Tipos dos exercícios: vêm do contrato (web/src/contract.ts). Aqui fica só o filtro de tipos conhecidos.
import type {
  LearnPhraseExercise,
  LearnSignExercise,
  MatchPairsExercise,
  PhraseToTextExercise,
  SignToTextExercise,
  SignToWordExercise,
  WordToSignExercise,
} from "../../contract";

export type LearnSign = LearnSignExercise;
export type SignToWord = SignToWordExercise;
export type WordToSign = WordToSignExercise;
export type MatchPairs = MatchPairsExercise;
export type LearnPhrase = LearnPhraseExercise;
export type PhraseToText = PhraseToTextExercise;
export type SignToText = SignToTextExercise;

export type KnownExercise = LearnSign | SignToWord | WordToSign | MatchPairs | LearnPhrase | PhraseToText | SignToText;
// A API pode ganhar tipos novos: o front precisa sobreviver a eles.
export type Exercise = KnownExercise | { id: string; type: string; [k: string]: unknown };

const KNOWN = new Set(["learn_sign", "sign_to_word", "word_to_sign", "match_pairs", "learn_phrase", "phrase_to_text", "sign_to_text"]);

export function isKnownExercise(e: Exercise): e is KnownExercise {
  return KNOWN.has(e.type);
}

/** Cartões de apresentação: não valem nota, contam como acerto ao continuar. */
export function isIntroCard(e: KnownExercise): e is LearnSign | LearnPhrase {
  return e.type === "learn_sign" || e.type === "learn_phrase";
}

/** Descarta tipos desconhecidos antes de começar, para que `total` bata com o que a pessoa realmente jogou. */
export function playableExercises(exercises: Exercise[]): KnownExercise[] {
  return exercises.filter(isKnownExercise);
}
