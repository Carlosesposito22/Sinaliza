import { describe, expect, it } from "vitest";
import type { DictionaryEntry } from "../../contract";
import { filterDictionary, fold, initial } from "./dictionary";

const e = (gloss: string, word: string, seen: boolean, forms: string[] = [word]): DictionaryEntry => ({
  gloss, word, forms, theme_ids: [], seen, mistakes: 0,
});
const signs = [e("MÃE", "mãe", true), e("COMPREENDER", "entender", true, ["compreender", "entender"]), e("ÁGUA", "água", false)];

describe("dictionary", () => {
  it("ignora acento e maiúscula", () => {
    expect(fold("  Mãe ")).toBe("mae");
    expect(initial("Água")).toBe("A");
  });
  it("mostra só os vistos em 'meus sinais' e todos em 'todos'", () => {
    expect(filterDictionary(signs, "seen", "").map((s) => s.gloss)).toEqual(["MÃE", "COMPREENDER"]);
    expect(filterDictionary(signs, "all", "")).toHaveLength(3);
  });
  it("busca na palavra e nas outras formas", () => {
    expect(filterDictionary(signs, "all", "agua").map((s) => s.gloss)).toEqual(["ÁGUA"]);
    expect(filterDictionary(signs, "seen", "compre").map((s) => s.gloss)).toEqual(["COMPREENDER"]);
    expect(filterDictionary(signs, "seen", "agua")).toEqual([]);
  });
});
