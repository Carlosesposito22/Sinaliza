import { useEffect, useState } from "react";
import { Link, Navigate, useParams } from "react-router-dom";
import type { LessonStatus } from "../contract";
import { fetchProgress } from "../learnApi";

// Placeholder do M1: só garante que lição bloqueada não abre. O fluxo da lição (M2) entra aqui.
export function LessonPage() {
  const { id = "" } = useParams();
  const [status, setStatus] = useState<LessonStatus | "loading" | "error">("loading");

  useEffect(() => {
    fetchProgress()
      .then((p) => setStatus(p.lessons[id]?.status ?? "locked"))
      .catch(() => setStatus("error"));
  }, [id]);

  if (status === "locked") return <Navigate to="/" replace />;
  return (
    <div className="status">
      <p>{status === "loading" ? "Carregando…" : status === "error" ? "Não foi possível abrir a lição." : `Lição ${id}: em construção.`}</p>
      <Link to="/">Voltar à trilha</Link>
    </div>
  );
}
