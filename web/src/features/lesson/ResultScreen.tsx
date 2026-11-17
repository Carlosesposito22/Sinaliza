// Tela de fim de aula ou treino: acerto, estrelas, XP e o que abriu. Só front; não é ML.
import type { ReactNode } from "react";
import { Star } from "lucide-react";
import { percent } from "../trail/trail";

interface Props {
  passed: boolean;
  accuracy: number;
  stars?: number;
  xp: number;
  title: string;
  lines?: ReactNode[];
  actions: ReactNode;
}

export function ResultScreen({ passed, accuracy, stars, xp, title, lines = [], actions }: Props) {
  return (
    <main className="exam">
      <section className={`exam-score-card ${passed ? "passed" : "failed"}`} aria-live="polite">
        {stars !== undefined && (
          <p className="result-stars" aria-label={`${stars} de 3 estrelas`}>
            {[0, 1, 2].map((i) => (
              <Star key={i} className={i < stars ? "star on" : "star"} aria-hidden="true" />
            ))}
          </p>
        )}
        <p className="exam-score">{percent(accuracy)}%</p>
        <h1>{title}</h1>
        {xp > 0 && <p>+{xp} XP</p>}
        {lines.map((line, i) => (
          <p key={i}>{line}</p>
        ))}
        <div className="exam-actions">{actions}</div>
      </section>
    </main>
  );
}
