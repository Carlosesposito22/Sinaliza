import { describe, expect, it } from "vitest";
import type { AchievementInfo } from "../../contract";
import { achievementPercent, achievementProgressLabel, formatDay, groupAchievements } from "./achievements";

const a = (id: string, category: AchievementInfo["category"], extra: Partial<AchievementInfo> = {}): AchievementInfo => ({
  id, title: id, description: "", kind: "medal", tier: "bronze", category, icon: "star",
  unlocked: false, unlocked_at: null, current: 0, target: 1, ...extra,
});

describe("achievements", () => {
  it("agrupa por categoria na ordem da tela e conta as ganhas", () => {
    const groups = groupAchievements([
      a("x", "habito"), a("y", "provas", { unlocked: true }), a("z", "temas"), a("w", "provas"),
    ]);
    expect(groups.map((g) => g.category)).toEqual(["temas", "provas", "habito"]);
    expect(groups[1]).toMatchObject({ label: "Provas", unlocked: 1 });
    expect(groups[1].items.map((i) => i.id)).toEqual(["y", "w"]);
  });
  it("calcula a barra e o rótulo de contagem", () => {
    expect(achievementPercent(a("p", "provas", { current: 2, target: 5 }))).toBe(40);
    expect(achievementPercent(a("p", "provas", { unlocked: true, current: 5, target: 5 }))).toBe(100);
    expect(achievementProgressLabel(a("p", "provas", { current: 2, target: 5 }))).toBe("2/5");
    expect(achievementProgressLabel(a("p", "provas"))).toBeNull();
    expect(achievementProgressLabel(a("p", "provas", { unlocked: true, target: 5 }))).toBeNull();
  });
  it("formata a data sem fuso", () => {
    expect(formatDay("2026-11-17")).toBe("17/11/2026");
    expect(formatDay(null)).toBe("");
  });
});
