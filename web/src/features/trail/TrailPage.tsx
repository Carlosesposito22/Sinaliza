// Tela inicial: a trilha de temas em forma de caminho. Cada tema tem aulas (sinais e frases) e termina
// numa prova; passar na prova abre o próximo tema. Os dados vêm do LearnContext (GET /learn/path e
// /learn/progress) e se atualizam sozinhos quando uma aula ou prova termina. Só front; não é ML.
import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import {
  BookOpen, Check, GraduationCap, Heart, Home, Lock, MessageCircle, Play, RotateCcw, Star, Stethoscope, Sun,
  Trophy, Users, Utensils, Zap, type LucideIcon,
} from "lucide-react";
import type { LessonSummary, Progress, Theme } from "../../contract";
import { useLearn } from "../progress/LearnContext";
import { StatsBar } from "../progress/StatsBar";
import { ErrorView, LoadingView } from "../progress/StatusViews";
import { currentStep, lessonStatus, nodeOffset, percent, themeSummary, type Step } from "./trail";

// Ícone por tema: casa pelo id/título (sem acento). Tema novo cai no fallback.
const THEME_ICONS: [RegExp, LucideIcon][] = [
  [/escola|aula|estud/, GraduationCap],
  [/saude|hospital|medic/, Stethoscope],
  [/famil/, Users],
  [/dia.?a.?dia|rotina|cotidian/, Sun],
  [/casa|lar/, Home],
  [/comida|aliment|cozinha/, Utensils],
  [/sentiment|emoc/, Heart],
  [/cumpriment|saudac|conversa/, MessageCircle],
];

function themeIcon(theme: Theme): LucideIcon {
  const key = `${theme.id} ${theme.title}`.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  return THEME_ICONS.find(([re]) => re.test(key))?.[1] ?? BookOpen;
}

function Stars({ count }: { count: number }) {
  return (
    <>
      {[0, 1, 2].map((i) => (
        <Star key={i} size={14} className={i < count ? "star on" : "star"} />
      ))}
    </>
  );
}

const isStep = (step: Step | null, kind: Step["kind"], id: string) =>
  step !== null && step.kind === kind && (step.kind === "lesson" ? step.id : step.themeId) === id;

export function TrailPage() {
  const { path, progress, error, loading, justUnlocked, reload } = useLearn();
  const step = currentStep(path, progress);
  const stepKey = step ? `${step.kind}:${step.kind === "lesson" ? step.id : step.themeId}` : null;
  const currentRef = useRef<HTMLLIElement | null>(null);

  // Ao abrir, rola até o passo atual (sem animação se a pessoa pediu menos movimento).
  useEffect(() => {
    if (!currentRef.current) return;
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    currentRef.current.scrollIntoView({ block: "center", behavior: reduce ? "auto" : "smooth" });
  }, [stepKey]);

  if (error && !path) return <ErrorView message={error} onRetry={() => void reload()} />;
  if (loading && (!path || !progress)) return <LoadingView label="Carregando a trilha…" />;
  if (!path || !progress) return null;
  if (path.themes.length === 0) return <p className="status">A trilha ainda não tem temas.</p>;

  let index = 0; // posição global do nó, para a curva continuar entre os temas
  return (
    <>
      <StatsBar progress={progress} />
      <PracticeCards progress={progress} />
      <p className="disclaimer">{path.disclaimer}</p>
      {path.themes.map((theme, t) => {
        const s = themeSummary(theme, progress);
        const ThemeIcon = themeIcon(theme);
        const locked = s.status === "locked";
        const previous = t > 0 ? path.themes[t - 1].title : null;
        return (
          <section key={theme.id} className={locked ? "unit theme-locked" : "unit"} aria-labelledby={`theme-${theme.id}`}>
            <div className="unit-head" style={{ background: locked ? undefined : theme.color }}>
              <h2 id={`theme-${theme.id}`}>
                {locked ? <Lock size={20} aria-hidden="true" /> : <ThemeIcon size={22} aria-hidden="true" />} {theme.title}
                {justUnlocked.includes(theme.id) && <span className="theme-new">Novo!</span>}
              </h2>
              <p>{locked && previous ? `Passe na prova de ${previous} para abrir este tema.` : theme.description}</p>
              {!locked && (
                <p className="unit-count">
                  {s.completed}/{s.total} aulas · {s.stars}/{s.total * 3} <Star size={13} aria-label="estrelas" />
                  {s.status === "passed" && ` · prova ${percent(s.bestScore)}%`}
                </p>
              )}
            </div>
            {s.mustRedo && s.lastScore !== null && (
              <p className="redo-banner" role="status">
                <RotateCcw size={16} aria-hidden="true" /> Você tirou {percent(s.lastScore)}% na prova (mínimo{" "}
                {percent(theme.exam.pass_score)}%). Refaça as aulas marcadas para tentar de novo.
              </p>
            )}
            <ol className="path">
              {theme.lessons.map((lesson) => {
                const offset = nodeOffset(index++);
                const current = isStep(step, "lesson", lesson.id);
                return (
                  <li key={lesson.id} ref={current ? currentRef : undefined} className="path-step" style={{ ["--offset" as string]: offset }}>
                    <LessonNode
                      lesson={lesson}
                      progress={progress}
                      color={theme.color}
                      isCurrent={current}
                      isNew={justUnlocked.includes(lesson.id)}
                    />
                  </li>
                );
              })}
              {(() => {
                const offset = nodeOffset(index++);
                const current = isStep(step, "exam", theme.id);
                return (
                  <li ref={current ? currentRef : undefined} className="path-step" style={{ ["--offset" as string]: offset }}>
                    <ExamNode theme={theme} progress={progress} isCurrent={current} />
                  </li>
                );
              })()}
            </ol>
          </section>
        );
      })}
    </>
  );
}

// Treino fora da trilha: desafio do dia e revisão dos erros. Só aparecem quando há o que fazer.
function PracticeCards({ progress }: { progress: Progress }) {
  if (!progress.challenge_available && progress.review_signs === 0) return null;
  return (
    <div className="practice-cards">
      {progress.challenge_available && (
        <Link to="/desafio" className={progress.challenge_done_today ? "practice-card done" : "practice-card"}>
          <Zap aria-hidden="true" />
          <span>
            <strong>Desafio do dia</strong>
            <span className="muted">{progress.challenge_done_today ? "Feito hoje ✓ · treinar de novo" : "Sinais que você já viu · +15 XP"}</span>
          </span>
        </Link>
      )}
      {progress.review_signs > 0 && (
        <Link to="/revisao" className="practice-card review">
          <RotateCcw aria-hidden="true" />
          <span>
            <strong>Revisar erros</strong>
            <span className="muted">
              {progress.review_signs} {progress.review_signs === 1 ? "sinal" : "sinais"} para treinar · +10 XP
            </span>
          </span>
        </Link>
      )}
    </div>
  );
}

interface NodeProps {
  lesson: LessonSummary;
  progress: Progress;
  color: string;
  isCurrent: boolean;
  isNew: boolean;
}

function LessonNode({ lesson, progress, color, isCurrent, isNew }: NodeProps) {
  const status = lessonStatus(progress, lesson.id);
  const lp = progress.lessons[lesson.id];
  const starCount = lp?.stars ?? 0;
  const redo = lp?.needs_redo ?? false;
  const KindIcon = lesson.kind === "phrases" ? MessageCircle : Play;

  if (status === "locked") {
    return (
      <div className="node-wrap">
        <span className="node-circle locked" role="img" aria-label={`${lesson.title}: bloqueada`}>
          <Lock aria-hidden="true" />
        </span>
        <span className="node-title muted">{lesson.title}</span>
      </div>
    );
  }

  const label =
    status === "completed"
      ? `${lesson.title}: concluída com ${starCount} de 3 estrelas. Refazer`
      : redo
        ? `${lesson.title}: refazer para liberar a prova`
        : `${lesson.title}: começar`;
  return (
    <div className="node-wrap">
      {isCurrent && (
        <span className="node-bubble" aria-hidden="true">
          {redo ? "Refazer" : isNew ? "Nova! Começar" : "Começar"}
        </span>
      )}
      <Link
        to={`/licao/${lesson.id}`}
        className={`node-circle ${status}${isCurrent ? " current" : ""}${redo ? " redo" : ""}`}
        style={status === "available" && !isCurrent && !redo ? { background: color } : undefined}
        aria-label={label}
      >
        {status === "completed" ? <Check aria-hidden="true" /> : redo ? <RotateCcw aria-hidden="true" /> : <KindIcon aria-hidden="true" />}
      </Link>
      <span className="node-title">
        {lesson.title}
        {redo && <span className="node-tag">refazer</span>}
      </span>
      {starCount > 0 && (
        <span className="node-stars" aria-hidden="true">
          <Stars count={starCount} />
        </span>
      )}
    </div>
  );
}

function ExamNode({ theme, progress, isCurrent }: { theme: Theme; progress: Progress; isCurrent: boolean }) {
  const s = themeSummary(theme, progress);
  const title = `Prova: ${theme.title}`;
  if (s.status === "locked" || s.status === "learning") {
    return (
      <div className="node-wrap">
        <span className="node-circle locked exam-node" role="img" aria-label={`${title}: bloqueada até concluir as aulas`}>
          <Trophy aria-hidden="true" />
        </span>
        <span className="node-title muted">{title}</span>
        <span className="node-sub muted">{theme.exam.n_questions} questões</span>
      </div>
    );
  }
  const passed = s.status === "passed";
  return (
    <div className="node-wrap">
      {isCurrent && (
        <span className="node-bubble" aria-hidden="true">
          {s.attempts > 0 ? "Tentar de novo" : "Fazer a prova"}
        </span>
      )}
      <Link
        to={`/prova/${theme.id}`}
        className={`node-circle exam-node ${passed ? "completed" : "available"}${isCurrent ? " current" : ""}`}
        aria-label={passed ? `${title}: aprovada com ${percent(s.bestScore)}%. Refazer` : `${title}: começar`}
      >
        <Trophy aria-hidden="true" />
      </Link>
      <span className="node-title">{title}</span>
      <span className="node-sub muted">
        {passed ? `aprovada · ${percent(s.bestScore)}%` : `mínimo ${percent(theme.exam.pass_score)}%`}
      </span>
    </div>
  );
}
