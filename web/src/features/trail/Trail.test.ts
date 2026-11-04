import { describe, expect, it } from "vitest";
import type { Progress } from "../../contract";
import { goalPercent, lessonStatus, stars } from "./Trail";

const progress = {
  lessons: {
    a: { status: "completed", stars: 3, best_accuracy: 1, completions: 1 },
    b: { status: "available", stars: 0, best_accuracy: 0, completions: 0 },
  },
} as unknown as Progress;

describe("trail", () => {
  it("lê o estado da lição e bloqueia o desconhecido", () => {
    expect(lessonStatus(progress, "a")).toBe("completed");
    expect(lessonStatus(progress, "b")).toBe("available");
    expect(lessonStatus(progress, "x")).toBe("locked");
    expect(lessonStatus(null, "a")).toBe("locked");
  });
  it("desenha estrelas limitadas a 0–3", () => {
    expect(stars(2)).toBe("★★☆");
    expect(stars(9)).toBe("★★★");
    expect(stars(-1)).toBe("☆☆☆");
  });
  it("calcula o percentual da meta sem passar de 100", () => {
    expect(goalPercent(10, 20)).toBe(50);
    expect(goalPercent(45, 20)).toBe(100);
    expect(goalPercent(5, 0)).toBe(0);
  });
});
