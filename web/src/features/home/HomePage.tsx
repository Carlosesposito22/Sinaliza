// Página inicial: a marca em destaque, o botão para o próximo passo e as portas para cada parte do app.
// Os dados vêm do LearnContext (trilha e progresso) e de GET /learn/achievements. Só front; não é ML.
import { useEffect, useState, type CSSProperties, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, BookOpenText, Flame, Medal, MessageSquareText, RotateCcw, Route, Trophy, Zap } from "lucide-react";
import type { AchievementsResponse } from "../../contract";
import { fetchAchievements } from "../../learnApi";
import { Logo } from "../../ui/Logo";
import { useLearn } from "../progress/LearnContext";
import { profileStats } from "../trail/trail";
import { nextAction } from "./home";

export function HomePage() {
  const { path, progress, error, reload } = useLearn();
  const [achievements, setAchievements] = useState<AchievementsResponse | null>(null);

  useEffect(() => {
    fetchAchievements().then(setAchievements, () => setAchievements(null));
  }, [progress]);

  const next = nextAction(path, progress);
  const stats = profileStats(path, progress);

  return (
    <main className="home">
      <section className="hero" aria-labelledby="hero-title">
        <div className="hero-bg" aria-hidden="true" />
        <h1 id="hero-title" className="visually-hidden">
          Sinaliza
        </h1>
        <Logo size="hero" tagline />
        <p className="hero-lead">
          Aprenda os primeiros sinais vendo um avatar: tema por tema, com aulas curtas, prática escrita e uma prova no fim.
        </p>
        <Link to={next.to} className="btn btn-primary btn-lg hero-cta">
          <span>
            {next.label}
            {next.detail && <small>{next.detail}</small>}
          </span>
          <ArrowRight aria-hidden="true" />
        </Link>
        {progress && (
          <ul className="hero-stats" aria-label="Seu progresso">
            <li>
              <Flame aria-hidden="true" className="ic-flame" />
              <strong>{progress.streak_days}</strong> {progress.streak_days === 1 ? "dia" : "dias"}
            </li>
            <li>
              <Zap aria-hidden="true" className="ic-zap" />
              <strong>{progress.xp}</strong> XP
            </li>
            <li>
              <Medal aria-hidden="true" className="ic-medal" />
              Nível <strong>{progress.level}</strong>
            </li>
          </ul>
        )}
        {error && !progress && (
          <p className="hero-error" role="alert">
            {error}{" "}
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => void reload()}>
              Tentar de novo
            </button>
          </p>
        )}
      </section>

      <section className="home-grid" aria-label="O que fazer">
        <HomeCard
          to="/trilha"
          tone="blue"
          icon={<Route />}
          title="Trilha"
          text={path ? `${stats.themesPassed} de ${stats.themesTotal} temas aprovados` : "Temas com aulas e prova"}
        />
        <HomeCard
          to="/desafio"
          tone="yellow"
          icon={<Zap />}
          title="Desafio do dia"
          text={
            !progress?.challenge_available
              ? "Abre depois da primeira aula"
              : progress.challenge_done_today
                ? "Feito hoje ✓"
                : "Sinais que você já viu · +15 XP"
          }
          muted={!progress?.challenge_available}
        />
        <HomeCard
          to="/revisao"
          tone="orange"
          icon={<RotateCcw />}
          title="Revisar erros"
          text={progress?.review_signs ? `${progress.review_signs} ${progress.review_signs === 1 ? "sinal" : "sinais"} para treinar` : "Nada pendente"}
          badge={progress?.review_signs || undefined}
          muted={!progress?.review_signs}
        />
        <HomeCard to="/dicionario" tone="green" icon={<BookOpenText />} title="Dicionário" text={`${stats.signsLearned} vistos · 210 sinais`} />
        <HomeCard
          to="/conquistas"
          tone="purple"
          icon={<Trophy />}
          title="Conquistas"
          text={achievements ? `${achievements.unlocked_count} de ${achievements.total} na coleção` : "Medalhas e troféus"}
        />
        <HomeCard to="/tradutor" tone="teal" icon={<MessageSquareText />} title="Texto em sinais" text="Digite uma frase e veja a sequência" />
      </section>

      <p className="disclaimer home-disclaimer">
        {path?.disclaimer ?? "Os sinais e frases não foram validados por falante de Libras. É uma sequência de sinais, não uma tradução."}
      </p>
    </main>
  );
}

interface CardProps {
  to: string;
  tone: "blue" | "yellow" | "orange" | "green" | "purple" | "teal";
  icon: ReactNode;
  title: string;
  text: string;
  badge?: number;
  muted?: boolean;
}

function HomeCard({ to, tone, icon, title, text, badge, muted }: CardProps) {
  return (
    <Link to={to} className={muted ? "home-card muted-card" : "home-card"} style={{ "--tone": `var(--${tone})` } as CSSProperties}>
      <span className="home-card-icon" aria-hidden="true">
        {icon}
        {badge ? <span className="home-card-badge">{badge}</span> : null}
      </span>
      <span className="home-card-text">
        <strong>{title}</strong>
        <span>{text}</span>
      </span>
      <ArrowRight className="home-card-arrow" aria-hidden="true" />
    </Link>
  );
}
