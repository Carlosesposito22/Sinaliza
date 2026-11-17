// Regras de exibição das conquistas (só front; não é ML). Quem decide quem ganhou o quê é a API.
import type { AchievementCategory, AchievementInfo, AchievementTier } from "../../contract";

export const CATEGORY_LABELS: Record<AchievementCategory, string> = {
  temas: "Temas",
  provas: "Provas",
  aulas: "Aulas",
  habito: "Hábito",
};

// Ordem das seções na tela. Categoria desconhecida vai para o fim.
const CATEGORY_ORDER: AchievementCategory[] = ["temas", "provas", "aulas", "habito"];

export const TIER_LABELS: Record<AchievementTier, string> = { bronze: "bronze", silver: "prata", gold: "ouro" };

export interface AchievementGroup {
  category: AchievementCategory;
  label: string;
  items: AchievementInfo[];
  unlocked: number;
}

// Agrupa por categoria mantendo a ordem do catálogo dentro de cada grupo.
export function groupAchievements(items: AchievementInfo[]): AchievementGroup[] {
  const groups = new Map<AchievementCategory, AchievementInfo[]>();
  for (const item of items) groups.set(item.category, [...(groups.get(item.category) ?? []), item]);
  const rank = (c: AchievementCategory) => {
    const i = CATEGORY_ORDER.indexOf(c);
    return i === -1 ? CATEGORY_ORDER.length : i;
  };
  return [...groups.entries()]
    .sort(([a], [b]) => rank(a) - rank(b))
    .map(([category, list]) => ({
      category,
      label: CATEGORY_LABELS[category] ?? category,
      items: list,
      unlocked: list.filter((a) => a.unlocked).length,
    }));
}

// Percentual da barra de uma conquista de contagem (0 a 100). Ganha = 100.
export function achievementPercent(a: AchievementInfo): number {
  if (a.unlocked) return 100;
  return a.target > 0 ? Math.min(100, Math.round((a.current / a.target) * 100)) : 0;
}

// Texto curto do progresso: "2/5" só para conquistas de contagem ainda não ganhas.
export function achievementProgressLabel(a: AchievementInfo): string | null {
  return !a.unlocked && a.target > 1 ? `${a.current}/${a.target}` : null;
}

// "2026-11-17" → "17/11/2026" sem passar por Date (evita erro de fuso).
export function formatDay(iso: string | null): string {
  if (!iso) return "";
  const [y, m, d] = iso.split("-");
  return d && m && y ? `${d}/${m}/${y}` : iso;
}
