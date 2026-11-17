// Estado da trilha compartilhado entre as telas (trilha, perfil, aula, prova, conquistas). Só front; não é ML.
//
// Carrega GET /learn/path e GET /learn/progress uma vez. Quando uma aula ou prova termina, quem chamou a API
// passa a resposta para `applyResult` / `applyExamResult`: o progresso novo já vem nela, então a trilha e o
// perfil se atualizam sem recarregar a página. As conquistas ganhas ficam em `newAchievements` até alguém
// mostrá-las (o aviso no Layout) e chamar `dismissAchievements`.
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { AchievementInfo, ExamResult, LessonResult, PathResponse, PracticeResult, Progress } from "../../contract";
import { fetchPath, fetchProgress } from "../../learnApi";

interface LearnValue {
  path: PathResponse | null;
  progress: Progress | null;
  error: string | null;
  loading: boolean;
  // Aulas e temas liberados pela última aula ou prova (para a trilha destacar como "novo").
  justUnlocked: string[];
  // Conquistas ganhas e ainda não mostradas.
  newAchievements: AchievementInfo[];
  reload: () => Promise<void>;
  applyResult: (result: LessonResult) => void;
  applyExamResult: (result: ExamResult) => void;
  applyPracticeResult: (result: PracticeResult) => void;
  dismissAchievements: () => void;
}

const LearnContext = createContext<LearnValue | null>(null);

export function LearnProvider({ children }: { children: ReactNode }) {
  const [path, setPath] = useState<PathResponse | null>(null);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [justUnlocked, setJustUnlocked] = useState<string[]>([]);
  const [newAchievements, setNewAchievements] = useState<AchievementInfo[]>([]);

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

  const celebrate = useCallback((earned: AchievementInfo[] | undefined) => {
    if (earned?.length) setNewAchievements((current) => [...current, ...earned]);
  }, []);

  const applyResult = useCallback(
    (result: LessonResult) => {
      setProgress(result.progress);
      setJustUnlocked(result.unlocked_lesson_ids);
      celebrate(result.new_achievements);
    },
    [celebrate],
  );

  const applyExamResult = useCallback(
    (result: ExamResult) => {
      setProgress(result.progress);
      setJustUnlocked(result.unlocked_theme_ids);
      celebrate(result.new_achievements);
    },
    [celebrate],
  );

  const applyPracticeResult = useCallback(
    (result: PracticeResult) => {
      setProgress(result.progress);
      celebrate(result.new_achievements);
    },
    [celebrate],
  );

  const dismissAchievements = useCallback(() => setNewAchievements([]), []);

  const value = useMemo(
    () => ({
      path, progress, error, loading, justUnlocked, newAchievements,
      reload, applyResult, applyExamResult, applyPracticeResult, dismissAchievements,
    }),
    [
      path, progress, error, loading, justUnlocked, newAchievements,
      reload, applyResult, applyExamResult, applyPracticeResult, dismissAchievements,
    ],
  );
  return <LearnContext.Provider value={value}>{children}</LearnContext.Provider>;
}

export function useLearn(): LearnValue {
  const value = useContext(LearnContext);
  if (!value) throw new Error("useLearn precisa estar dentro de <LearnProvider>.");
  return value;
}
