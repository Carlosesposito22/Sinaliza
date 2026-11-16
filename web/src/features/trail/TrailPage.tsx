// Tela inicial: a trilha em forma de caminho. Os dados vêm do LearnContext (GET /learn/path e /learn/progress)
// e se atualizam sozinhos quando uma lição termina (applyResult). Só front; não é ML.
import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import {
  BookOpen, Check, Hand, Heart, Home, Lock, MessageCircle, Play, Star, Sun, Users, Utensils,
  type LucideIcon,
} from "lucide-react";
import type { LessonSummary, Progress, Unit } from "../../contract";
import { useLearn } from "../progress/LearnContext";
import { StatsBar } from "../progress/StatsBar";
import { ErrorView, LoadingView } from "../progress/StatusViews";
import { currentLessonId, lessonStatus, nodeOffset, unitSummary } from "./trail";

// Ícone por unidade: casa pelo id/título (sem acento). Unidade nova cai no fallback.
const UNIT_ICONS: [RegExp, LucideIcon][] = [
  [/famil/, Users],
  [/dia.?a.?dia|rotina|cotidian/, Sun],
  [/casa|lar/, Home],
  [/comida|aliment|cozinha/, Utensils],
  [/sentiment|emoc/, Heart],
  [/cumpriment|saudac|conversa|frase/, MessageCircle],
  [/alfabeto|letra|manual/, Hand],
];

function unitIcon(unit: Unit): LucideIcon {
  const key = `${unit.id} ${unit.title}`.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  return UNIT_ICONS.find(([re]) => re.test(key))?.[1] ?? BookOpen;
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

export function TrailPage() {
  const { path, progress, error, loading, justUnlocked, reload } = useLearn();
  const currentId = currentLessonId(path, progress);
  const currentRef = useRef<HTMLLIElement | null>(null);

  // Ao abrir, rola até a lição atual (sem animação se a pessoa pediu menos movimento).
  useEffect(() => {
    if (!currentRef.current) return;
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    currentRef.current.scrollIntoView({ block: "center", behavior: reduce ? "auto" : "smooth" });
  }, [currentId]);

  if (error && !path) return <ErrorView message={error} onRetry={() => void reload()} />;
  if (loading && (!path || !progress)) return <LoadingView label="Carregando a trilha…" />;
  if (!path || !progress) return null;
  if (path.units.length === 0) return <p className="status">A trilha ainda não tem lições.</p>;

  let index = 0; // posição global do nó, para a curva continuar entre as unidades
  return (
    <>
      <StatsBar progress={progress} />
      <p className="disclaimer">{path.disclaimer}</p>
      {path.units.map((unit) => {
        const summary = unitSummary(unit, progress);
        const UnitIcon = unitIcon(unit);
        return (
          <section key={unit.id} className="unit" aria-labelledby={`unit-${unit.id}`}>
            <div className="unit-head" style={{ background: unit.color }}>
              <h2 id={`unit-${unit.id}`}>
                <UnitIcon size={22} aria-hidden="true" /> {unit.title}
              </h2>
              <p>{unit.description}</p>
              <p className="unit-count">
                {summary.completed}/{summary.total} lições · {summary.stars}/{summary.total * 3}{" "}
                <Star size={13} aria-label="estrelas" />
              </p>
            </div>
            <ol className="path">
              {unit.lessons.map((lesson) => {
                const offset = nodeOffset(index++);
                const isCurrent = lesson.id === currentId;
                return (
                  <li
                    key={lesson.id}
                    ref={isCurrent ? currentRef : undefined}
                    className="path-step"
                    style={{ ["--offset" as string]: offset }}
                  >
                    <LessonNode
                      lesson={lesson}
                      progress={progress}
                      color={unit.color}
                      isCurrent={isCurrent}
                      isNew={justUnlocked.includes(lesson.id)}
                    />
                  </li>
                );
              })}
            </ol>
          </section>
        );
      })}
    </>
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
  const starCount = progress.lessons[lesson.id]?.stars ?? 0;

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
      : `${lesson.title}: começar`;
  return (
    <div className="node-wrap">
      {isCurrent && (
        <span className="node-bubble" aria-hidden="true">
          {isNew ? "Nova! Começar" : "Começar"}
        </span>
      )}
      <Link
        to={`/licao/${lesson.id}`}
        className={`node-circle ${status}${isCurrent ? " current" : ""}`}
        style={status === "available" ? { background: color } : undefined}
        aria-label={label}
      >
        {status === "completed" ? <Check aria-hidden="true" /> : <Play aria-hidden="true" />}
      </Link>
      <span className="node-title">{lesson.title}</span>
      {status === "completed" && (
        <span className="node-stars" aria-hidden="true">
          <Stars count={starCount} />
        </span>
      )}
    </div>
  );
}