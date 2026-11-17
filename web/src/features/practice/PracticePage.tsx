// Treino fora da trilha: "Revisão dos erros" (/revisao) e "Desafio do dia" (/desafio). Os exercícios vêm da
// API (só sinais do vocabulário curado que a pessoa já viu ou errou) e são jogados no mesmo ExercisePlayer
// das aulas. Regra, não ML.
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { CompleteRequest, Practice, PracticeResult } from "../../contract";
import { completePractice, fetchChallenge, fetchReview } from "../../learnApi";
import { useLearn } from "../progress/LearnContext";
import { LoadingView } from "../progress/StatusViews";
import { ExercisePlayer } from "../lesson/ExercisePlayer";
import { ResultScreen } from "../lesson/ResultScreen";

const TEXT = {
  review: {
    fetch: fetchReview,
    empty: "Nada para revisar agora.",
    emptyDetail: "Os sinais que você errar em aulas, provas e desafios aparecem aqui para treinar de novo.",
  },
  challenge: {
    fetch: fetchChallenge,
    empty: "O desafio do dia ainda não está disponível.",
    emptyDetail: "Conclua uma aula: o desafio sorteia sinais que você já viu.",
  },
} as const;

export function PracticePage({ kind }: { kind: "review" | "challenge" }) {
  const { applyPracticeResult } = useLearn();
  const [session, setSession] = useState<Practice | null>(null);
  const [result, setResult] = useState<PracticeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const text = TEXT[kind];

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      setSession(await text.fetch());
    } catch (e) {
      setSession(null);
      setError(e instanceof Error ? e.message : "Não foi possível abrir o treino.");
    } finally {
      setLoading(false);
    }
  }, [text]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) return <LoadingView label="Preparando o treino…" />;
  if (!session) {
    return (
      <div className="status">
        <p>{text.empty}</p>
        <p className="muted">{error && !error.startsWith("nada") && !error.startsWith("conclua") ? error : text.emptyDetail}</p>
        <Link to="/trilha">Voltar à trilha</Link>
      </div>
    );
  }

  if (result) {
    const lines = [];
    if (kind === "review") {
      const left = result.progress.review_signs;
      lines.push(
        result.cleared_glosses.length > 0
          ? `${result.cleared_glosses.length} ${result.cleared_glosses.length === 1 ? "sinal saiu" : "sinais saíram"} da revisão.`
          : "Nenhum sinal saiu da revisão desta vez.",
      );
      lines.push(left > 0 ? `Ainda há ${left} para revisar.` : "Sua revisão está em dia!");
    } else if (session.completed_today) {
      lines.push("Você já tinha feito o desafio de hoje: este foi só treino, sem XP.");
    } else if (result.passed) {
      lines.push("Desafio de hoje cumprido! Volte amanhã para um novo.");
    } else {
      lines.push("Acerte pelo menos 60% para cumprir o desafio. Pode tentar de novo.");
    }
    if (result.goal_reached_now) lines.push("Meta de hoje cumprida!");
    return (
      <ResultScreen
        passed={result.passed}
        accuracy={result.accuracy}
        xp={result.xp_gained}
        title={result.passed ? "Treino concluído!" : "Ainda não foi desta vez."}
        lines={lines}
        actions={
          <>
            <Link to="/trilha" className="btn btn-primary">
              Voltar à trilha
            </Link>
            {(kind === "challenge" || result.progress.review_signs > 0) && (
              <button type="button" className="btn btn-secondary" onClick={() => void load()}>
                {kind === "review" ? "Revisar de novo" : "Tentar de novo"}
              </button>
            )}
          </>
        }
      />
    );
  }

  const onFinish = async (request: CompleteRequest) => {
    const done = await completePractice(session.id, request);
    applyPracticeResult(done);
    setResult(done);
    window.scrollTo({ top: 0 });
  };
  const accent = kind === "review" ? "var(--orange)" : "var(--yellow-strong)";
  return <ExercisePlayer key={session.id} title={session.title} accent={accent} exercises={session.exercises} onFinish={onFinish} />;
}
