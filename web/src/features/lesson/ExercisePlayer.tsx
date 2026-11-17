// Joga uma lista de exercícios, um por tela, com barra de progresso e feedback (estilo Duolingo).
// Usado pela aula, pela revisão dos erros e pelo desafio do dia. O estado é o LessonReducer.
// Só front; não é ML. Feedback é só visual (sem som: o público pode ser surdo).
import { useEffect, useReducer, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { Check, X } from "lucide-react";
import type { CompleteRequest, Exercise } from "../../contract";
import { ExerciseView } from "./Exercises";
import { isIntroCard, playableExercises } from "./exerciceTypes";
import { vlibrasPlayer } from "../../vlibras";
import { initLesson, lessonReducer, progressFraction, toCompleteRequest } from "./LessonReducer";

interface Props {
  title: string;
  accent?: string; // cor do tema (CSS), usada na barra e nos destaques
  exercises: Exercise[];
  onFinish: (request: CompleteRequest) => Promise<void>;
}

export function ExercisePlayer({ title, accent, exercises, onFinish }: Props) {
  const [state, dispatch] = useReducer(lessonReducer, exercises, (list) => initLesson(playableExercises(list)));
  const [detail, setDetail] = useState<ReactNode>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sent = useRef(false);

  const finish = async () => {
    setSaving(true);
    setError(null);
    try {
      await onFinish(toCompleteRequest(state));
    } catch (e) {
      sent.current = false;
      setError(e instanceof Error ? e.message : "Não foi possível salvar o resultado.");
      setSaving(false);
    }
  };

  useEffect(() => {
    if (state.phase === "finished" && !sent.current) {
      sent.current = true;
      void finish();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.phase]);

  const current = state.exercises[state.index];
  const percent = Math.round(progressFraction(state) * 100);

  // A legenda do player escreve a glosa, que é a resposta. Desligada enquanto a pessoa responde; ligada nos
  // cartões de apresentação (a palavra já está na tela) e no feedback. Volta ao normal ao sair.
  const subtitles = state.phase !== "answering" || (current ? isIntroCard(current) : true);
  useEffect(() => {
    vlibrasPlayer().setSubtitles(subtitles);
  }, [subtitles]);
  useEffect(() => () => vlibrasPlayer().setSubtitles(true), []);

  return (
    <main className="exam player" style={accent ? ({ "--theme": accent } as CSSProperties) : undefined}>
      <div className="exam-progress">
        <span className="exam-progress-row">
          {title}
          <Link to="/trilha" className="exam-exit" aria-label="Sair (o progresso desta aula não é salvo)">
            <X size={16} aria-hidden="true" /> Sair
          </Link>
        </span>
        <div className="bar" role="progressbar" aria-label="Progresso" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent}>
          <div className="bar-fill" style={{ width: `${percent}%` }} />
        </div>
      </div>

      {state.phase === "finished" ? (
        <div className="status">
          {error ? (
            <>
              <p className="error">{error}</p>
              <button type="button" onClick={() => void finish()} disabled={saving}>
                Tentar de novo
              </button>
            </>
          ) : (
            <p>Salvando o resultado…</p>
          )}
        </div>
      ) : (
        current && (
          <ExerciseView
            key={current.id}
            exercise={current}
            locked={state.phase === "feedback"}
            onAcknowledge={() => dispatch({ type: "acknowledge" })}
            onAnswer={(correct, info) => {
              setDetail(info ?? null);
              dispatch({ type: "answer", correct });
            }}
          />
        )
      )}

      {state.phase === "feedback" && (
        <div className={state.lastWasCorrect ? "feedback right" : "feedback wrong"} role="status" aria-live="polite">
          <p className="feedback-title">
            {state.lastWasCorrect ? <Check aria-hidden="true" /> : <X aria-hidden="true" />}
            {state.lastWasCorrect ? "Muito bem!" : "Quase! Veja a resposta:"}
          </p>
          {detail && <p className="feedback-detail">{detail}</p>}
          <button type="button" className="btn btn-primary" autoFocus onClick={() => dispatch({ type: "next" })}>
            Continuar
          </button>
        </div>
      )}
    </main>
  );
}
