// Estado da trilha compartilhado entre as telas (trilha, perfil, lição, resultado). Só front; não é ML.
//
// Carrega GET /learn/path e GET /learn/progress uma vez. Quando uma lição termina, quem chamou
// POST /learn/lessons/{id}/complete passa a resposta para `applyResult`: o progresso novo já vem nela,
// então a trilha e o perfil se atualizam sem recarregar a página nem chamar a API de novo.
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { LessonResult, PathResponse, Progress } from "../../contract";
import { fetchPath, fetchProgress } from "../../learnApi";

interface LearnValue {
  path: PathResponse | null;
  progress: Progress | null;
  error: string | null;
  loading: boolean;
  // Lições liberadas pela última lição concluída (para a trilha destacar como "nova").
  justUnlocked: string[];
  reload: () => Promise<void>;
  applyResult: (result: LessonResult) => void;
}

const LearnContext = createContext<LearnValue | null>(null);

export function LearnProvider({ children }: { children: ReactNode }) {
  const [path, setPath] = useState<PathResponse | null>(null);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [justUnlocked, setJustUnlocked] = useState<string[]>([]);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [p, pr] = await Promise.all([fetchPath(), fetchProgress()]);
      setPath(p);
      setProgress(pr);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Não foi possível falar com a API.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const applyResult = useCallback((result: LessonResult) => {
    setProgress(result.progress);
    setJustUnlocked(result.unlocked_lesson_ids);
  }, []);

  const value = useMemo(
    () => ({ path, progress, error, loading, justUnlocked, reload, applyResult }),
    [path, progress, error, loading, justUnlocked, reload, applyResult],
  );
  return <LearnContext.Provider value={value}>{children}</LearnContext.Provider>;
}

export function useLearn(): LearnValue {
  const value = useContext(LearnContext);
  if (!value) throw new Error("useLearn precisa estar dentro de <LearnProvider>.");
  return value;
}
