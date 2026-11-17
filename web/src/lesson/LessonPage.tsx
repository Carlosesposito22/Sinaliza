// Aula da trilha: busca GET /learn/lessons/{id}, joga os exercícios (ExercisePlayer) e registra o resultado
// em POST /learn/lessons/{id}/complete. A resposta já traz o progresso novo (applyResult), então a trilha,
// o perfil e as conquistas se atualizam sem recarregar. Só front; não é ML.
import { useCallback, useEffect, useState } from "react";
import { Link, Navigate, useParams } from "react-router-dom";
import type { CompleteRequest, Lesson, LessonResult } from "../contract";
import { completeLesson, fetchLesson } from "../learnApi";
import { useLearn } from "../features/progress/LearnContext";
import { ErrorView, LoadingView } from "../features/progress/StatusViews";
import { ExercisePlayer } from "../features/lesson/ExercisePlayer";
import { ResultScreen } from "../features/lesson/ResultScreen";
import { lessonStatus } from "../features/trail/trail";

export function LessonPage() {
  const { id = "" } = useParams();
  const { path, progress, loading, error: learnError, reload, applyResult } = useLearn();
  const [lesson, setLesson] = useState<Lesson | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<LessonResult | null>(null);
  const [attempt, setAttempt] = useState(0);

  const load = useCallback(async () => {
    setError(null);
    setResult(null);
    try {
      setLesson(await fetchLesson(id));
      setAttempt((n) => n + 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Não foi possível abrir a aula.");
    }
  }, [id]);

  const status = lessonStatus(progress, id);
  useEffect(() => {
    if (progress && status !== "locked") void load();
    // carrega uma vez por aula; o progresso muda ao terminar e não deve recarregar a aula
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, progress === null]);

  if (learnError && !progress) return <ErrorView message={learnError} onRetry={() => void reload()} />;
  if (loading && !progress) return <LoadingView label="Carregando…" />;
  if (!progress) return null;
  if (status === "locked" && !result) return <Navigate to="/trilha" replace />;
  if (error) return <ErrorView message={error} onRetry={() => void load()} />;
  if (!lesson) return <LoadingView label="Preparando a aula…" />;

  if (result) {
    const theme = path?.themes.find((t) => t.id === lesson.theme_id);
    const lines = [];
    if (!result.passed) lines.push("Para a aula contar, acerte pelo menos 60%. Sem pressa: dá para refazer quantas vezes quiser.");
    if (result.bonus_perfect) lines.push("Aula perfeita: +5 XP de bônus.");
    if (result.exam_unlocked && theme) lines.push(`Todas as aulas de ${theme.title} feitas: a prova do tema abriu!`);
    if (result.level_up) lines.push(`Você subiu para o nível ${result.progress.level}.`);
    if (result.goal_reached_now) lines.push("Meta de hoje cumprida!");
    if (result.progress.review_signs > 0) lines.push(`${result.progress.review_signs} sinais esperando revisão.`);
    return (
      <ResultScreen
        passed={result.passed}
        accuracy={result.accuracy}
        stars={result.stars}
        xp={result.xp_gained}
        title={result.passed ? "Aula concluída!" : "Ainda não foi desta vez."}
        lines={lines}
        actions={
          <>
            {result.exam_unlocked && theme ? (
              <Link to={`/prova/${theme.id}`} className="btn btn-primary">
                Fazer a prova
              </Link>
            ) : (
              <Link to="/trilha" className="btn btn-primary">
                Voltar à trilha
              </Link>
            )}
            <button type="button" className="btn btn-secondary" onClick={() => void load()}>
              Refazer a aula
            </button>
          </>
        }
      />
    );
  }

  const onFinish = async (request: CompleteRequest) => {
    const done = await completeLesson(id, request);
    applyResult(done);
    setResult(done);
    window.scrollTo({ top: 0 });
  };
  const color = path?.themes.find((t) => t.id === lesson.theme_id)?.color;
  return (
    <ExercisePlayer key={`${lesson.id}-${attempt}`} title={lesson.title} accent={color} exercises={lesson.exercises} onFinish={onFinish} />
  );
}
