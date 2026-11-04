import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { PathResponse, Progress } from "../../contract";
import { fetchPath, fetchProgress } from "../../learnApi";
import { goalPercent, lessonStatus, stars } from "./Trail";

const STATE_LABEL = { locked: "Bloqueada", available: "Começar", completed: "Concluída" } as const;

export function TrailPage() {
  const [path, setPath] = useState<PathResponse | null>(null);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [p, pr] = await Promise.all([fetchPath(), fetchProgress()]);
      setPath(p);
      setProgress(pr);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Não foi possível falar com a API.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (error) {
    return (
      <div className="status" role="alert">
        <p className="error">{error}</p>
        <button type="button" onClick={() => void load()}>
          Tentar de novo
        </button>
      </div>
    );
  }
  if (!path || !progress) return <p className="status">Carregando a trilha…</p>;

  return (
    <>
      <header className="stats">
        <span>🔥 {progress.streak_days} dias</span>
        <span>⚡ {progress.xp} XP</span>
        <span>Nível {progress.level}</span>
        <label className="goal">
          Meta de hoje: {progress.xp_today}/{progress.daily_goal_xp} XP
          <progress max={100} value={goalPercent(progress.xp_today, progress.daily_goal_xp)} />
        </label>
      </header>
      {path.units.map((unit) => (
        <section key={unit.id} className="unit" aria-label={unit.title}>
          <div className="unit-head" style={{ background: unit.color }}>
            <h2>
              {unit.icon} {unit.title}
            </h2>
            <p>{unit.description}</p>
          </div>
          <ul className="nodes">
            {unit.lessons.map((lesson) => {
              const status = lessonStatus(progress, lesson.id);
              const done = progress.lessons[lesson.id]?.stars ?? 0;
              const body = (
                <>
                  <span>{lesson.title}</span>
                  <span className="node-state">
                    {status === "completed" ? `${stars(done)} ` : ""}
                    {STATE_LABEL[status]}
                  </span>
                </>
              );
              return (
                <li key={lesson.id}>
                  {status === "locked" ? (
                    <span className="node locked" aria-disabled="true">
                      {body}
                    </span>
                  ) : (
                    <Link className={`node ${status}`} to={`/licao/${lesson.id}`}>
                      {body}
                    </Link>
                  )}
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </>
  );
}
