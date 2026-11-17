// O desenho de uma conquista: medalha (círculo) ou troféu (escudo), na cor do nível (bronze, prata, ouro).
// Bloqueada fica em cinza com cadeado. Só front; não é ML.
import {
  Award, BookOpen, CircleCheck, ClipboardCheck, Crown, Flame, Hand, History, Lock, Rocket, RotateCcw, Star, TrendingUp, Trophy, Zap,
  type LucideIcon,
} from "lucide-react";
import type { AchievementInfo } from "../../contract";

const ICONS: Record<string, LucideIcon> = {
  exam: ClipboardCheck,
  check: CircleCheck,
  star: Star,
  rocket: Rocket,
  comeback: RotateCcw,
  hand: Hand,
  book: BookOpen,
  flame: Flame,
  level: TrendingUp,
  trophy: Trophy,
  crown: Crown,
  review: History,
  bolt: Zap,
};

export function Badge({ achievement, size = "md" }: { achievement: AchievementInfo; size?: "sm" | "md" }) {
  const Icon = ICONS[achievement.icon] ?? Award;
  const locked = !achievement.unlocked;
  return (
    <span
      className={`badge badge-${achievement.kind} tier-${achievement.tier} badge-${size}${locked ? " locked" : ""}`}
      aria-hidden="true"
    >
      <Icon className="badge-icon" />
      {locked && (
        <span className="badge-lock">
          <Lock />
        </span>
      )}
    </span>
  );
}
