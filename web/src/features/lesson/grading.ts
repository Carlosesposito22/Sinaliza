import type { SignToWord, WordToSign } from "./exerciceTypes";

/** sign_to_word e word_to_sign: compara o id da opção escolhida com o gabarito. */
export function gradeChoice(exercise: SignToWord | WordToSign, selectedOptionId: string): boolean {
  return exercise.correct_option_id === selectedOptionId;
}

/**
 * match_pairs: o sinal e a palavra escolhidos formam um par se vêm do mesmo `pairs[].id`.
 */
export function isPairMatch(signPairId: string, wordPairId: string): boolean {
  return signPairId === wordPairId;
}

// TODO: confirmar com o Carlos se match_pairs conta como 1 exercício (como está) ou 1 por par.
export function gradeMatchPairs(wrongAttempts: number): boolean {
  return wrongAttempts === 0;
}