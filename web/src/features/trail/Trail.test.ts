import { describe, expect, it } from "vitest";
import type { PathResponse, Progress } from "../../contract";
import {
  currentLessonId,
  goalPercent,
  lessonStatus,
  levelPercent,
  nodeOffset,
  profileStats,
  stars,
  unitSummary,
} from "./trail";

const progress = {
  xp: 130,
  xp_in_level: 30,
  xp_to_next_level: 70,
  lessons: {
    a: { status: "completed", stars: 3, best_accuracy: 1, completions: 1 },
    b: { status: "available", stars: 0, best_accuracy: 0, completions: 0 },
    c: { status: "locked", stars: 0, best_accuracy: 0, completions: 0 },
  },
} as unknown as Progress;

const lesson = (id: string, glosses: string[]) => ({ id, title: id, xp_reward: 20, n_exercises: 13, glosses });
const path: PathResponse = {
  title: "Trilha",
  disclaimer: "aviso",
  units: [
    { id: "u1", title: "U1", description: "", color: "#fff", icon: "x", lessons: [lesson("a", ["MÃE", "PAI"]), lesson("b", ["PAI", "FILHO"])] },
    { id: "u2", title: "U2", description: "", color: "#fff", icon: "y", lessons: [lesson("c", ["CASA"])] },
  ],
};

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
  it("desloca os nós em curva e repete o padrão", () => {
    expect([0, 1, 2, 3, 4, 5, 6, 7].map(nodeOffset)).toEqual([0, 1, 2, 1, 0, -1, -2, -1]);
    expect(nodeOffset(8)).toBe(0);
  });
  it("acha a lição atual (a primeira disponível)", () => {
    expect(currentLessonId(path, progress)).toBe("b");
    expect(currentLessonId(null, progress)).toBeNull();
    const allDone = { ...progress, lessons: { a: progress.lessons.a } } as Progress;
    expect(currentLessonId(path, allDone)).toBeNull();
  });
  it("resume uma unidade", () => {
    expect(unitSummary(path.units[0], progress)).toEqual({ completed: 1, total: 2, stars: 3 });
    expect(unitSummary(path.units[1], null)).toEqual({ completed: 0, total: 1, stars: 0 });
  });
  it("calcula os números do perfil (sinais distintos só das concluídas)", () => {
    expect(profileStats(path, progress)).toEqual({
      lessonsCompleted: 1,
      lessonsTotal: 3,
      stars: 3,
      maxStars: 9,
      signsLearned: 2,
      unitsCompleted: 0,
      unitsTotal: 2,
    });
  });
  it("calcula o percentual do nível", () => {
    expect(levelPercent(progress)).toBe(30);
  });
});
