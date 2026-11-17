// Cabeçalho fixo da trilha: sequência, XP, nível e meta do dia.
import { Flame, Medal, Zap } from "lucide-react";
import type { Progress } from "../../contract";
import { goalPercent } from "../trail/trail";

export function StatsBar({ progress }: { progress: Progress }) {
  const goal = goalPercent(progress.xp_today, progress.daily_goal_xp);
  return (
    <header className="stats" aria-label="Seu progresso">
      <div className="stat-row">
        <span className="stat" title="Sequência de dias">
          <Flame size={18} className="ic ic-flame" aria-hidden="true" /> {progress.streak_days}{" "}
          {progress.streak_days === 1 ? "dia" : "dias"}
        </span>
        <span className="stat" title="Experiência total">
          <Zap size={18} className="ic ic-zap" aria-hidden="true" /> {progress.xp} XP
        </span>
        <span className="stat" title="Nível">
          <Medal size={18} className="ic ic-medal" aria-hidden="true" /> Nível {progress.level}
        </span>
      </div>
      <div className="goal">
        <div className="goal-label">
          <span>Meta de hoje</span>
          <span>
            {progress.goal_reached_today ? "✔ cumprida! " : ""}
            {progress.xp_today}/{progress.daily_goal_xp} XP
          </span>
        </div>
        <div
          className="bar"
          role="progressbar"
          aria-label="Meta de hoje"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={goal}
        >
          <div className={progress.goal_reached_today ? "bar-fill done" : "bar-fill"} style={{ width: `${goal}%` }} />
        </div>
      </div>
    </header>
  );
}