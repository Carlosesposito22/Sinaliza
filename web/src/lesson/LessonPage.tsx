import { useState } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";
import { completeLesson } from "../learnApi";
import { useLearn } from "../features/progress/LearnContext";
import { lessonStatus } from "../features/trail/trail";

// Placeholder do M1: só garante que lição bloqueada não abre. O fluxo da lição (M2, Caio) entra aqui.
// Ao terminar a lição, o fluxo deve chamar `completeLesson(id, ...)` e passar a resposta para
// `applyResult` (de useLearn): a trilha e o perfil se atualizam sem recarregar.
export function LessonPage() {
  const { id = "" } = useParams();
  const { progress, loading, error } = useLearn();

  if (loading && !progress) return <p className="status">Carregando…</p>;
  if (!progress) {
    return (
      <div className="status">
        <p className="error">{error ?? "Não foi possível abrir a lição."}</p>
        <Link to="/">Voltar à trilha</Link>
      </div>
    );
  }
  if (lessonStatus(progress, id) === "locked") return <Navigate to="/" replace />;
  return (
    <div className="status">
      <p>Lição {id}: em construção.</p>
      <Link to="/">Voltar à trilha</Link>
      {import.meta.env.DEV && <DevSimulate lessonId={id} />}
    </div>
  );
}

// TEMPORÁRIO, só no `npm run dev` (não entra no build): simula o fim da lição para testar a trilha
// e o perfil antes de as telas dos exercícios existirem. Apagar quando o fluxo da lição (M2) chegar.
function DevSimulate({ lessonId }: { lessonId: string }) {
  const { applyResult } = useLearn();
  const navigate = useNavigate();
  const [msg, setMsg] = useState<string | null>(null);

  async function simulate(correct: number) {
    setMsg(null);
    try {
      const result = await completeLesson(lessonId, { correct, total: 13, mistakes: [] });
      applyResult(result);
      navigate("/");
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Falhou.");
    }
  }

  return (
    <fieldset className="dev-box">
      <legend>Só no modo de desenvolvimento</legend>
      <p className="muted">Simular o fim desta lição (13 exercícios):</p>
      <div className="dev-actions">
        <button type="button" onClick={() => void simulate(13)}>13/13 (perfeita)</button>
        <button type="button" onClick={() => void simulate(10)}>10/13 (2 ★)</button>
        <button type="button" onClick={() => void simulate(5)}>5/13 (reprova)</button>
      </div>
      {msg && <p className="error">{msg}</p>}
    </fieldset>
  );
}
