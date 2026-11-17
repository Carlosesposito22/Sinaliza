// Perfil: XP, nível, sequência e o que a pessoa já concluiu. Tudo vem de GET /learn/progress e /learn/path
// (via LearnContext). O perfil é anônimo: o id fica guardado só neste navegador.
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { ThemeToggle } from "../../ui/ThemeToggle";
import { BookOpen, Flame, Hand, Map as MapIcon, Medal, Star, Target, Trophy } from "lucide-react";
import { useLearn } from "./LearnContext";
import { ErrorView, LoadingView } from "./StatusViews";
import { goalPercent, levelPercent, profileStats } from "../trail/trail";

export function ProfilePage() {
  const { path, progress, error, loading, reload } = useLearn();

  if (error && !progress) return <ErrorView message={error} onRetry={() => void reload()} />;
  if (loading && (!path || !progress)) return <LoadingView label="Carregando o perfil…" />;
  if (!path || !progress) return null;

  const s = profileStats(path, progress);
  const level = levelPercent(progress);
  const goal = goalPercent(progress.xp_today, progress.daily_goal_xp);

  return (
    <main className="profile">
      <h1>Seu progresso</h1>
      <p className="muted">Perfil anônimo, guardado só neste navegador.</p>

      <section className="card" aria-labelledby="nivel">
        <h2 id="nivel">
          <Medal size={18} className="ic ic-medal" aria-hidden="true" /> Nível {progress.level}
        </h2>
        <p>
          {progress.xp} XP no total · faltam {progress.xp_to_next_level} XP para o nível {progress.level + 1}
        </p>
        <div className="bar" role="progressbar" aria-label="Progresso no nível" aria-valuemin={0} aria-valuemax={100} aria-valuenow={level}>
          <div className="bar-fill" style={{ width: `${level}%` }} />
        </div>
      </section>

      <div className="tiles">
        <Tile icon={<Flame />} value={progress.streak_days} label={progress.streak_days === 1 ? "dia seguido" : "dias seguidos"} />
        <Tile icon={<Trophy />} value={progress.best_streak} label="melhor sequência" />
        <Tile icon={<BookOpen />} value={`${s.lessonsCompleted}/${s.lessonsTotal}`} label="lições concluídas" />
        <Tile icon={<Star />} value={`${s.stars}/${s.maxStars}`} label="estrelas" />
        <Tile icon={<Hand />} value={s.signsLearned} label="sinais vistos" />
        <Tile icon={<MapIcon />} value={`${s.themesPassed}/${s.themesTotal}`} label="temas aprovados" />
      </div>

      <section className="card" aria-labelledby="meta">
        <h2 id="meta">
          <Target size={18} className="ic ic-zap" aria-hidden="true" /> Meta de hoje
        </h2>
        <p>
          {progress.xp_today}/{progress.daily_goal_xp} XP{progress.goal_reached_today ? " · cumprida!" : ""}
        </p>
        <div className="bar" role="progressbar" aria-label="Meta de hoje" aria-valuemin={0} aria-valuemax={100} aria-valuenow={goal}>
          <div className={progress.goal_reached_today ? "bar-fill done" : "bar-fill"} style={{ width: `${goal}%` }} />
        </div>
        {progress.last_activity_date && <p className="muted">Última lição em {formatDate(progress.last_activity_date)}.</p>}
      </section>

      <section className="card profile-links" aria-label="Preferências e informações">
        <ThemeToggle withLabel />
        <Link to="/tradutor">Texto em sinais</Link>
        <Link to="/sobre">Sobre o Sinaliza, créditos e avisos</Link>
      </section>
    </main>
  );
}

function Tile({ icon, value, label }: { icon: ReactNode; value: number | string; label: string }) {
  return (
    <div className="tile">
      <span className="tile-icon" aria-hidden="true">
        {icon}
      </span>
      <strong className="tile-value">{value}</strong>
      <span className="tile-label">{label}</span>
    </div>
  );
}

// "2026-11-16" → "16/11/2026" sem passar por Date (evita erro de fuso).
function formatDate(iso: string): string {
  const [y, m, d] = iso.split("-");
  return d && m && y ? `${d}/${m}/${y}` : iso;
}