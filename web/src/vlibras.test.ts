import { describe, expect, it } from "vitest";
import { toVlibrasGloss } from "./vlibras";

describe("toVlibrasGloss", () => {
  it("junta as glosas com espaço e usa _ nos sinais de várias palavras", () => {
    expect(toVlibrasGloss(["EU", "CADEIRA DE RODAS", "POR FAVOR"])).toBe("EU CADEIRA_DE_RODAS POR_FAVOR");
  });

  it("troca as glosas que o dicionário do VLibras não tem por sinais que ele tem", () => {
    expect(toVlibrasGloss(["FILHO", "DOR DE CABEÇA"])).toBe("FILHO DOR CABEÇA");
    expect(toVlibrasGloss(["COM SEDE"])).toBe("SEDE");
  });

  it("devolve vazio sem glosas", () => {
    expect(toVlibrasGloss([])).toBe("");
  });
});
