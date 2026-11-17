// Aba "Conquistas": a coleção de medalhas e troféus, ganhos ou não. Os dados vêm de GET /learn/achievements;
// quem decide as regras é a API (regra, não ML). Recarrega quando o progresso muda.
import { useCallback, useEffect, useState } from "react";
import type { AchievementsResponse } from "../../contract";
import { fetchAchievements } from "../../learnApi";
import { useLearn } from "../progress/LearnContext";
import { ErrorView, LoadingView } from "../progress/StatusViews";
import { Badge } from "./Badge";
import { TIER_LABELS, achievementPercent, achievementProgressLabel, formatDay, groupAchievements } from "./achievements";

export function AchievementsPage() {
  const { progress } = useLearn();
  const [data, setData] = useState<AchievementsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setData(await fetchAchievements());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Não foi possível carregar as conquistas.");
    }
  }, []);

  // `progress` muda depois de cada aula ou prova: é a deixa para buscar de novo.
  useEffect(() => {
    void load();
  }, [load, progress]);

  if (error && !data) return <ErrorView message={error} onRetry={() => void load()} />;
  if (!data) return <LoadingView label="Carregando as conquistas…" />;

  const percent = data.total > 0 ? Math.round((data.unlocked_count / data.total) * 100) : 0;
  return (
    <main className="achievements">
      <h1>Conquistas</h1>
      <p className="muted">Medalhas e troféus que você ganha estudando: provas, temas, aulas e dias seguidos.</p>
      <section className="card" aria-labelledby="colecao">
        <h2 id="colecao">
          {data.unlocked_count} de {data.total} na sua coleção
        </h2>
        <div className="bar" role="progressbar" aria-label="Conquistas ganhas" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent}>
          <div className="bar-fill" style={{ width: `${percent}%` }} />
        </div>
      </section>

      {groupAchievements(data.achievements).map((group) => (
        <section key={group.category} aria-labelledby={`grupo-${group.category}`}>
          <h2 id={`grupo-${group.category}`} className="achievements-group">
            {group.label} <span className="muted">{group.unlocked}/{group.items.length}</span>
          </h2>
          <ul className="achievement-grid">
            {group.items.map((a) => {
              const count = achievementProgressLabel(a);
              const label = `${a.kind === "trophy" ? "Troféu" : "Medalha"} de ${TIER_LABELS[a.tier]}`;
              return (
                <li key={a.id} className={a.unlocked ? "achievement unlocked" : "achievement"}>
                  <Badge achievement={a} />
                  <strong>{a.title}</strong>
                  <span className="achievement-desc">{a.description}</span>
                  <span className="achievement-meta">
                    {a.unlocked ? `${label} · ${formatDay(a.unlocked_at)}` : `${label} · bloqueada`}
                  </span>
                  {count && (
                    <span className="achievement-count">
                      <span className="bar" aria-hidden="true">
                        <span className="bar-fill" style={{ width: `${achievementPercent(a)}%` }} />
                      </span>
                      {count}
                    </span>
                  )}
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </main>
  );
}
