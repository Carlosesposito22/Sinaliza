// Aviso "Conquista desbloqueada!" que aparece em qualquer tela quando uma aula ou prova dá medalha ou troféu.
// Visual (sem som: o público pode ser surdo). Some sozinho depois de alguns segundos ou ao fechar.
import { useEffect } from "react";
import { Link } from "react-router-dom";
import { X } from "lucide-react";
import { useLearn } from "../progress/LearnContext";
import { Badge } from "./Badge";

const VISIBLE_MS = 8000;

export function AchievementToast() {
  const { newAchievements, dismissAchievements } = useLearn();

  useEffect(() => {
    if (newAchievements.length === 0) return;
    const timer = window.setTimeout(dismissAchievements, VISIBLE_MS);
    return () => window.clearTimeout(timer);
  }, [newAchievements, dismissAchievements]);

  if (newAchievements.length === 0) return null;
  const many = newAchievements.length > 1;
  return (
    <div className="achievement-toast" role="status" aria-live="polite">
      <div className="toast-badges">
        {newAchievements.slice(0, 4).map((a) => (
          <Badge key={a.id} achievement={a} size="sm" />
        ))}
      </div>
      <div className="toast-text">
        <strong>{many ? `${newAchievements.length} conquistas desbloqueadas!` : "Conquista desbloqueada!"}</strong>
        <span>{newAchievements.map((a) => a.title).join(" · ")}</span>
        <Link to="/conquistas" onClick={dismissAchievements}>
          Ver coleção
        </Link>
      </div>
      <button type="button" className="toast-close" aria-label="Fechar aviso" onClick={dismissAchievements}>
        <X size={16} aria-hidden="true" />
      </button>
    </div>
  );
}
